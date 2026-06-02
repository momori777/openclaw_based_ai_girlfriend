param(
    [int]$MaxAgeSeconds = 600,
    [switch]$WhatIf
)

$Now = Get-Date
$Killed = 0

Write-Host "[cleanup] start scanning for orphan processes..."

# ---- Llama Server health check + auto-restart ----
$llamaRunning = Get-Process llama-server -ErrorAction SilentlyContinue
$llamaHealthy = $false
if ($llamaRunning) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8080/health" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) { $llamaHealthy = $true }
    } catch { }
}

if (-not $llamaHealthy) {
    if ($llamaRunning) {
        Write-Host "[llama] process found but port 8080 not healthy, restarting..." -ForegroundColor Yellow
    } else {
        Write-Host "[llama] not running, starting..." -ForegroundColor Yellow
    }
    & "C:\Users\TK\.openclaw\workspace\restart-llama.ps1"
    Write-Host "[llama] restart script executed" -ForegroundColor Green
} else {
    Write-Host "[llama] healthy (PID=$($llamaRunning.Id))" -ForegroundColor Green
}

# Script keywords to match orphan processes
$ScriptPatterns = @(
    "comfyui_call\.py",
    "tts_call\.py"
)

$Processes = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Select-Object ProcessId, Name, CommandLine, CreationDate, ParentProcessId

$AlivePids = @{}
Get-Process | ForEach-Object { $AlivePids[$_.Id] = $true }

foreach ($Proc in $Processes) {
    $Cmd = $Proc.CommandLine
    $Pid = $Proc.ProcessId
    $Ppid = $Proc.ParentProcessId
    $Age = ($Now - $Proc.CreationDate).TotalSeconds

    $matched = $false
    foreach ($pattern in $ScriptPatterns) {
        if ($Cmd -match $pattern) {
            $matched = $true
            break
        }
    }
    if (-not $matched) { continue }

    $Reason = ""

    if ($Ppid -and -not $AlivePids.ContainsKey($Ppid)) {
        $Reason = "orphan (parent dead, PPID=$Ppid)"
    }
    elseif ($Age -gt $MaxAgeSeconds) {
        $parentAlive = $Ppid -and $AlivePids.ContainsKey($Ppid)
        if (-not $parentAlive) {
            $Reason = "timeout $([math]::Round($Age))s + parent dead"
        }
    }

    if ($Reason) {
        Write-Host "[cleanup] found orphan PID=$Pid (age=$Age s, $Reason)" -ForegroundColor Yellow
        $cmdPreview = if ($Cmd.Length -gt 120) { $Cmd.Substring(0, 120) + "..." } else { $Cmd }
        Write-Host "         cmd: $cmdPreview" -ForegroundColor Gray

        if (-not $WhatIf) {
            try {
                $childProcs = Get-CimInstance Win32_Process -Filter "ParentProcessId=$Pid" | Select-Object -ExpandProperty ProcessId
                Stop-Process -Id $Pid -Force -ErrorAction Stop
                foreach ($child in $childProcs) {
                    Stop-Process -Id $child -Force -ErrorAction SilentlyContinue
                }
                Write-Host "        killed (including $($childProcs.Count) children)" -ForegroundColor Green
                $Killed++
            } catch {
                Write-Host "        kill failed: $_" -ForegroundColor Red
            }
        }
    }
}

if ($WhatIf) {
    Write-Host "[cleanup] DRY RUN, no processes killed"
} else {
    Write-Host "[cleanup] done, killed $Killed orphans"
}

# Clean stale lock files
$LockFiles = @(
    "C:\Users\TK\.openclaw\workspace\comfyui_output\.comfyui_running.lock"
)
foreach ($LockFile in $LockFiles) {
    if (-not (Test-Path $LockFile)) { continue }
    try {
        $LockContent = Get-Content $LockFile -Raw | ConvertFrom-Json -ErrorAction SilentlyContinue
        if ($LockContent.Pid -and -not (Get-Process -Id $LockContent.Pid -ErrorAction SilentlyContinue)) {
            Remove-Item $LockFile -Force
            Write-Host "[cleanup] removed stale lock: $LockFile" -ForegroundColor Yellow
        }
    } catch {
        Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
        Write-Host "[cleanup] removed broken lock: $LockFile" -ForegroundColor Yellow
    }
}

# ---- Task flag cleanup ----
$TaskFlagDir = "C:\Users\TK\.openclaw\workspace\qqbot\.task_flags"
if (Test-Path $TaskFlagDir) {
    $FlagCutoff = (Get-Date).AddHours(-1)
    Get-ChildItem "$TaskFlagDir\*.done","$TaskFlagDir\*.meta.json" -ErrorAction SilentlyContinue | Where-Object {
        $_.CreationTime -lt $FlagCutoff
    } | ForEach-Object {
        Remove-Item $_.FullName -Force
        Write-Host "[cleanup] removed stale task flag: $($_.Name)" -ForegroundColor Gray
    }
    # Also remove any .done files that are complete (not needed after 1 hour)
    Get-ChildItem "$TaskFlagDir\*" -ErrorAction SilentlyContinue | Where-Object {
        $_.CreationTime -lt (Get-Date).AddHours(-2)
    } | ForEach-Object {
        Remove-Item $_.FullName -Force
        Write-Host "[cleanup] purged old flag file: $($_.Name)" -ForegroundColor DarkGray
    }
}

# ---- Session registry + orphan files cleanup ----
$SessionDirs = @(
    "C:\Users\TK\.openclaw\agents\main\sessions",
    "C:\Users\TK\.openclaw\agents\qqbot\sessions"
)

foreach ($AgentDir in $SessionDirs) {
    if (-not (Test-Path $AgentDir)) { continue }
    $RegFile = Join-Path $AgentDir "sessions.json"

    # 1. Collect valid session file IDs (actual jsonl files on disk)
    $ValidIds = @{}
    Get-ChildItem "$AgentDir\*.jsonl" -Exclude "*.checkpoint.*","*.trajectory.*","*.bak-*","*.cron.*" -ErrorAction SilentlyContinue | ForEach-Object {
        $ValidIds[$_.BaseName] = $true
    }

    # 2. Clean sessions.json stale entries
    if (Test-Path $RegFile) {
        try {
            $Raw = Get-Content $RegFile -Raw
            $Reg = ConvertFrom-Json $Raw -ErrorAction Stop
            $Changed = $false
            $KeysToRemove = @()

            foreach ($Key in $Reg.PSObject.Properties.Name) {
                $Entry = $Reg.$Key
                $SessionFilePath = $Entry.sessionFile
                $Status = $Entry.status
                $KeyType = $Entry.type -or ''

                # Rules in order:
                # 1. Key contains :subagent: or :spawn: and no sessionFile -> orphan subagent cleanup
                $IsSubagentSpawn = ($Key -match ':subagent:' -or $Key -match ':spawn:')
                # 2. sessionFile points to a file that does not exist
                $FileMissing = if ($SessionFilePath) { -not (Test-Path $SessionFilePath) } else { $false }
                # 3. No sessionFile at all and status is done/failed
                $NoFileStale = (-not $SessionFilePath) -and ($Status -in @('done','failed'))
                # 4. ended more than 1 hour ago
                $OldDone = $false
                if ($Entry.endedAt) {
                    try { $OldDone = ((Get-Date).ToUniversalTime() - (Get-Date '1970-01-01Z').AddMilliseconds($Entry.endedAt)).TotalHours -gt 1 } catch {}
                }

                # STALE = sessionFile missing + is subagent/spawn, OR no sessionFile + done/failed, OR ended long ago
                $IsStale = $false
                if ($IsSubagentSpawn -and (-not $SessionFilePath -or $FileMissing)) {
                    $IsStale = $true
                    Write-Host "[gateway-cleanup] stale subagent/spawn (no file): $Key" -ForegroundColor DarkYellow
                } elseif ($FileMissing) {
                    $IsStale = $true
                    Write-Host "[gateway-cleanup] stale session (file missing): $Key" -ForegroundColor DarkYellow
                } elseif ($NoFileStale -and $OldDone) {
                    $IsStale = $true
                    Write-Host "[gateway-cleanup] stale session (no file + done): $Key" -ForegroundColor DarkYellow
                }

                if ($IsStale) {
                    $KeysToRemove += $Key
                }
            }

            if ($KeysToRemove.Count -gt 0) {
                foreach ($Key in $KeysToRemove) {
                    $Reg.PSObject.Properties.Remove($Key)
                    $Changed = $true
                }
            }

            if ($Changed) {
                $Reg | ConvertTo-Json -Depth 10 | Set-Content $RegFile -Force
                Write-Host "[gateway-cleanup] updated $RegFile" -ForegroundColor Green
            } else {
                Write-Host "[gateway-cleanup] $RegFile clean" -ForegroundColor Gray
            }
        } catch {
            Write-Host "[gateway-cleanup] error processing $RegFile : $_" -ForegroundColor Red
        }
    }

    # 3. Force-clean any remaining .lock files (session write locks)
    # These are the main cause of "SessionWriteLockTimeoutError"
    Get-ChildItem "$AgentDir\*.lock" -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $LockFile = $_.FullName
            $LockPid = $null
            # Try to read PID from lock file
            try {
                $LockContent = Get-Content $LockFile -Raw -ErrorAction SilentlyContinue
                if ($LockContent -match 'pid=(\d+)') { $LockPid = [int]$Matches[1] }
            } catch {}
            
            if ($LockPid -and (Get-Process -Id $LockPid -ErrorAction SilentlyContinue)) {
                # Process still alive, check if it's a zombie (no active tcp connections, old creation time)
                $Proc = Get-Process -Id $LockPid -ErrorAction SilentlyContinue
                if ($Proc -and ((Get-Date) - $Proc.StartTime).TotalMinutes -gt 30) {
                    # Process running too long with lock → likely orphan
                    Stop-Process -Id $LockPid -Force -ErrorAction SilentlyContinue
                    Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
                    Write-Host "[cleanup] killed zombie process PID=$LockPid and removed its lock file" -ForegroundColor Yellow
                }
            } else {
                # No matching process → stale lock
                Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
                Write-Host "[cleanup] removed stale lock file: $($_.Name)" -ForegroundColor Yellow
            }
        } catch {
            Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
            Write-Host "[cleanup] force-removed orphan lock: $($_.Name)" -ForegroundColor Gray
        }
    }

    # 4. Purge .reset.* and .deleted.* files (backend renames old sessions on /new or session delete)
    $PurgedCount = 0
    Get-ChildItem "$AgentDir\*.reset.*","$AgentDir\*.deleted.*" -ErrorAction SilentlyContinue | ForEach-Object {
        Remove-Item $_.FullName -Force
        $PurgedCount++
        Write-Host "[cleanup] purged reset/deleted file: $($_.Name)" -ForegroundColor Gray
    }

    # 5. Collect known active session ids from sessions.json + existing jsonl files
    $KnownActiveIds = @()
    try {
        if (Test-Path $RegFile) {
            $Reg = Get-Content $RegFile -Raw | ConvertFrom-Json -ErrorAction SilentlyContinue
            # Support both formats: {sessions:[...]} (new) and {key:{...}} (old)
            if ($Reg -and $Reg.sessions) {
                $Reg.sessions | ForEach-Object {
                    if ($_.sessionId) { $KnownActiveIds += $_.sessionId }
                }
            } elseif ($Reg) {
                foreach ($Key in $Reg.PSObject.Properties.Name) {
                    $KnownActiveIds += $Key
                }
            }
        }
        # Also add all existing jsonl basenames as active
        Get-ChildItem "$AgentDir\*.jsonl" -Exclude "*.reset.*","*.deleted.*","*.trajectory.*","*.bak-*" -ErrorAction SilentlyContinue |
            ForEach-Object { if ($_.BaseName -notin $KnownActiveIds) { $KnownActiveIds += $_.BaseName } }
    } catch {}

    # 6. Clean stale jsonl files (not in sessions.json AND older than 2 hours)
    $Cutoff = (Get-Date).AddHours(-2)
    Get-ChildItem "$AgentDir\*.jsonl" -ErrorAction SilentlyContinue | ForEach-Object {
        $BaseId = $_.BaseName
        if ($BaseId -notin $KnownActiveIds -and $_.LastWriteTime -lt $Cutoff) {
            Remove-Item $_.FullName -Force
            Write-Host "[cleanup] removed orphan jsonl: $($_.Name)" -ForegroundColor Gray
            # Purge associated garbage
            Get-ChildItem "$AgentDir\$BaseId.*" -ErrorAction SilentlyContinue | Remove-Item -Force
        }
    }

    # 7. Clean trajectory / temp / lock files for non-active sessions
    $TrashPatterns = @("*.trajectory*","*.bak-*","*.lock","*.tmp")
    foreach ($Pattern in $TrashPatterns) {
        Get-ChildItem "$AgentDir\$Pattern" -ErrorAction SilentlyContinue | ForEach-Object {
            $BaseId = ($_.Name -split '\.')[0]
            if ($BaseId -notin $KnownActiveIds) {
                Remove-Item $_.FullName -Force
                Write-Host "[cleanup] removed trash: $($_.Name)" -ForegroundColor Gray
            }
        }
    }

    if ($PurgedCount -gt 0) { Write-Host "[cleanup] purged $PurgedCount reset/deleted files" -ForegroundColor Green }
}
