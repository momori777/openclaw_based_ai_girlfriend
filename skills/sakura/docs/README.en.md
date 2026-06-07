[中文](../README.md)

# Sakura Desktop Pet

A desktop companion Agent — chats, changes expressions, speaks, remembers what you allow, and helps with tasks after confirmation. It is not just a "desktop pet + chat" but a desktop companion Agent.

![Sakura Preview](../assets/sakura_01.png)

## Quick Start

**Prerequisites:** Python 3.10+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Edit data/config/api.yaml with your API Key
notepad data/config/api.yaml

python main.py
```

**Minimal `data/config/api.yaml`:**

```yaml
llm:
  base_url: https://api.openai.com/v1
  api_key: your_api_key_here
  model: gpt-4.1-mini
  timeout_seconds: 60
```

## Character Packs

Character packs (portraits, personality cards, voice resources) bring the pet to life. The project ships with a default character; additional ones are available from:

- **[GitHub Releases](https://github.com/Rvosy/sakura/releases)**: Download character pack zips (e.g. `mia.zip`) from the latest Release Assets.
- **[Baidu Netdisk](https://pan.baidu.com/s/1LnO25Ec2rezOnopjgX_OkQ?pwd=0721)**: Passcode `0721`, contains all published character packs.

### Installation

1. Download a character pack zip.
2. Extract it into the project root **`characters`** directory.
3. Ensure the structure is `characters/<id>/character.json` (one folder per character).
4. Restart the app — it auto-scans and loads new characters.

> Example: extracting `mia.zip` should yield `characters/mia/character.json`, `characters/mia/card.md`, `characters/mia/portraits/`, etc.

### Switching Characters

Right-click the pet or tray icon → Settings → pick a character from the list → Save.


## Project Structure

```
app/
  agent/         # Agent decision layer (AgentRuntime, tools, memory, MCP)
  core/          # App core (AppContext, bootstrap, ChatPipeline, debug)
  config/        # Config management (YAML read/write, models, migrations)
  llm/           # LLM client (OpenAI-compatible, ChatReply, prompts)
  plugins/       # Native plugin system (discovery, capabilities, manager)
  storage/       # Storage layer (StoragePaths, chat history, visual obs)
  ui/            # UI components (PetWindow, settings, history, portrait)
  voice/         # TTS providers (GPT-SoVITS, playback)
sdk/             # Shinsekai compat layer (deprecated, use app/plugins/)
plugins/         # Local plugins
data/config/     # YAML configuration files
tests/           # pytest tests
docs/            # Documentation (ARCHITECTURE.md, etc.)
```

## Configuration

All config in YAML under `data/config/`:

| YAML Path | Description | Default |
|---|---|---|
| `api.yaml: llm.base_url` | API base URL | `https://api.openai.com/v1` |
| `api.yaml: llm.api_key` | API Key | (empty) |
| `api.yaml: llm.model` | Model name | `gpt-4.1-mini` |
| `system_config.yaml: ui.subtitle_language` | Subtitle lang (`ja`/`zh`) | `ja` |
| `system_config.yaml: proactive_care.enabled` | Proactive care | `false` |
| `system_config.yaml: debug.enabled` | Debug logging | `false` |

## Testing

```powershell
python -m pytest
```
