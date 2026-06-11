# TOOLS.md — 能力中枢（速查版）

> AGENTS.md 是完整版，这个是精简速查。角色切换不改这个文件。

## 串行规则

TTS 和 ComfyUI 都停 llama-server（端口 8080）。不能同时 spawn。
必须等前一个 DONE: 后才 spawn 下一个。全部用 sessions_spawn(mode="run")。

## ComfyUI 画图

读 `skills/comfyui/prompt_template.md` -> 写 prompt -> spawn 子 session 跑 PS 脚本。

## TTS 语音

读 `memory/tts.md` -> spawn 子 session 跑 `skills/tts/run_tts.ps1`
语言: ja(默认)/zh/en  情绪: casual/tsundere/romantic/long/random

## Live2D

不杀 llama，直接 exec HTTP:
- `localhost:19200/api/motion?name=...`
- `localhost:19200/api/emotion?motion=...&text=...`
- `localhost:19200/api/message?text=...`
Motions: Idle, Tap外框, Tap摸头, Tap摸手, Start, Leave300_900_1800

## 角色记忆

`memory/role_play/<角色名>/` 下按日期存 markdown。
当前活跃角色 = SOUL.md 第一行声明的名字。

## 角色切换

```powershell
python D:\AI_Girlfriend\skills\character_importer\card_importer.py switch "card.png" --force
python D:\AI_Girlfriend\skills\character_importer\card_importer.py switch-harem natsume
```

切换后 /reset 重新加载。
