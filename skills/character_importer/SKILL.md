# Harem Manager — 角色卡导入 + 后宫管理

一键导入 SillyTavern 角色卡，存到后宫（harem）目录，随时切换女友。

## 核心设计

- **AGENTS.md** — 能力中枢（ComfyUI/TTS/Live2D），**角色切换不改它**
- **SOUL.md / IDENTITY.md** — 当前活跃角色，切换时覆写
- **skills/harem/<角色>/** — 后宫存档，每个角色独立目录
- **memory/role_play/<角色>/** — 每个角色的独立记忆

## 命令速查

```powershell
# 列出所有可用角色（后宫 + 卡片）
python skills\character_importer\card_importer.py list

# 预览角色卡
python skills\character_importer\card_importer.py preview "cards/Enola.png"

# 从 ST 角色卡切换（自动备份当前角色到 harem）
python skills\character_importer\card_importer.py switch "cards/Enola.png" --force

# 切回后宫中的角色
python skills\character_importer\card_importer.py switch-harem natsume
python skills\character_importer\card_importer.py switch-harem enola

# 列出 ST 聊天记录
python skills\character_importer\card_importer.py list-chats

# 导入对话记忆到 role_play/<角色>/
python skills\character_importer\card_importer.py import-chat "path/to/chat.jsonl" --force
```

## 工作流程

### 1. 从 chub.ai / ST 获取角色卡

下载 PNG 或 JSON 角色卡，放到 `skills/character_importer/cards/`

### 2. 一键切换

```powershell
python skills\character_importer\card_importer.py switch "cards/Enola.png" --force
```

会自动：
- 保存当前角色（SOUL+IDENTITY）到 `skills/harem/<旧角色>/`
- 写入新角色到根目录 + 同步到 OpenClaw workspace
- 在 `memory/role_play/<新角色>/` 创建记忆目录
- **不动 AGENTS.md**（能力中枢常驻）

### 3. 导入对话记忆（可选）

从 SillyTavern 导出的聊天 JSONL 文件，导入后存到 `memory/role_play/<角色>/`，下次切换角色时 agent 能读取上下文。

```powershell
# 列出 ST 聊天记录
python skills\character_importer\card_importer.py list-chats

# 导入对话到当前角色的记忆目录
python skills\character_importer\card_importer.py import-chat "C:/path/to/your/chat.jsonl" --force
```

> 注意：`import-chat` 接受任意路径的 `.jsonl` 文件。如果 ST 导出路径不在自动检测的目录（`Desktop/vllm/SillyTavern/data/default-user/chats`），直接传完整路径即可。

### 4. 重启加载

在对话中发 `/reset` 即可。

### 5. 切回来

```powershell
python skills\character_importer\card_importer.py switch-harem natsume
```

## 文件结构

```
skills/harem/
  natsume/           # 四季夏目
    SOUL.md
    IDENTITY.md
  enola/             # Enola (从 ST 导入)
    SOUL.md
    IDENTITY.md

memory/role_play/
  natsume/           # 夏目的记忆
    2026-06-11-live2d-test.md
  enola/             # Enola 的记忆
    2026-05-18-enola.md
```

## DIY 角色

直接在 `skills/harem/` 下新建目录，手写 SOUL.md 和 IDENTITY.md 即可。

SOUL.md 格式只需满足：
```markdown
# SOUL.md - 角色名

**核心设定：** 一句话概括。

## 性格
* 特点1
* 特点2

## 语气
* 风格描述
```
