@echo off
powershell -ExecutionPolicy Bypass -WindowStyle Hidden -NoProfile -File "%~dp0cleanup_orphans.ps1" -MaxAgeSeconds 600 >nul 2>&1
