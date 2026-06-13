#!/usr/bin/env python3
"""
Harem Manager — SillyTavern Character Card Importer for AI Girlfriend (Artemis)

Imports characters into skills/harem/<name>/ instead of overwriting root.
Switches active character by swapping SOUL.md + IDENTITY.md.
AGENTS.md is NEVER touched — it's the permanent ability hub.

Usage:
    python card_importer.py list                         # list all available cards + harem
    python card_importer.py preview <card_path>           # preview character info
    python card_importer.py switch <card_path>            # switch to a card (saves current to harem)
    python card_importer.py switch-harem <name>           # switch to a harem member
    python card_importer.py list-chats                    # list ST chat logs
    python card_importer.py import-chat <path>            # import chat to role_play
"""

import argparse
import base64
import json
import os
import re
import struct
import sys
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

# -- Paths ------------------------------------------------
WORKSPACE_ROOT = Path(__file__).resolve().parents[2]  # repo root (dev or runtime workspace)
OPENCLAW_WS = Path.home() / ".openclaw" / "workspace"  # runtime workspace

HAREM_DIR = WORKSPACE_ROOT / "skills" / "harem"
CARDS_DIR = WORKSPACE_ROOT / "skills" / "character_importer" / "cards"
ROLE_MEMORY_DIR = OPENCLAW_WS / "memory" / "role_play"

# SillyTavern directories — auto-detected or overridden via --st-dir / --chats-dir
_ST_HOME = (Path.home() / "Desktop" / "vllm" / "SillyTavern" / "data" / "default-user") if (Path.home() / "Desktop" / "vllm" / "SillyTavern").exists() else None
ST_CHARACTERS_DIR = _ST_HOME / "characters" if _ST_HOME else None
ST_CHATS_DIR = _ST_HOME / "chats" if _ST_HOME else None

# Files that are role-specific (swapped during switch)
ROLE_FILES = ["SOUL.md", "IDENTITY.md"]
ROOT_FILES = ["SOUL.md", "IDENTITY.md"]  # at workspace root

# TTS 权重切换相关
# 从 workspace/config.yaml 读取 sovits_root
import yaml as _yaml
_config_path = WORKSPACE_ROOT / "config.yaml"
if _config_path.exists():
    with open(_config_path, "r", encoding="utf-8") as _f:
        _cfg = _yaml.safe_load(_f)
    SOVITS_ROOT = Path(_cfg.get("sovits_root", ""))
    WEIGHT_JSON = SOVITS_ROOT / "weight.json" if SOVITS_ROOT.exists() else None
else:
    SOVITS_ROOT = None
    WEIGHT_JSON = None

def _switch_tts_weights(chara_name: str):
    """切换 GPT-SoVITS 的 weight.json 到指定角色的权重。
    规则: weight_<角色名>.json 存在则用它替换 weight.json。
    """
    if not WEIGHT_JSON or not WEIGHT_JSON.parent.exists():
        print("  [!] sovits_root 不存在，跳过 TTS 权重切换")
        return
    safe = chara_name.lower().replace(" ", "-")
    chara_weight = WEIGHT_JSON.parent / f"weight_{safe}.json"
    if chara_weight.exists():
        # 读取角色权重（处理可能的 BOM）
        try:
            with open(chara_weight, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            with open(chara_weight, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        # 写入不带 BOM 的 weight.json
        with open(WEIGHT_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"  [TTS] weight.json -> weight_{safe}.json")
    else:
        print(f"  [!] 未找到角色 TTS 权重: {chara_weight}")
        print(f"  [!] 请确保 weight_{safe}.json 存在，使用默认 weight.json")

# -- PNG/JSON Reading ---------------------------------------
def read_png_chara(png_path: Path) -> Optional[dict]:
    try:
        with open(png_path, "rb") as f:
            data = f.read()
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        pos = 8
        while pos < len(data):
            length = struct.unpack(">I", data[pos:pos+4])[0]
            pos += 4
            chunk_type = data[pos:pos+4].decode("ascii", errors="ignore")
            pos += 4
            chunk_data = data[pos:pos+length]
            pos += length + 4  # skip crc
            if chunk_type == "tEXt":
                null_idx = chunk_data.find(b"\0")
                keyword = chunk_data[:null_idx].decode("ascii", errors="ignore")
                text = chunk_data[null_idx+1:]
                if keyword == "chara":
                    try:
                        return json.loads(base64.b64decode(text))
                    except:
                        pass
                elif keyword == "ccv3":
                    try:
                        return json.loads(text)
                    except:
                        pass
        return None
    except Exception as e:
        print(f"  [!] Error reading {png_path.name}: {e}")
        return None

def _normalize_chara(raw: dict) -> Optional[dict]:
    if not raw:
        return None
    if "data" in raw and isinstance(raw.get("data"), dict):
        inner = raw["data"]
        if "name" in inner:
            return inner
    if "name" in raw:
        return raw
    return None

def read_json_chara(json_path: Path) -> Optional[dict]:
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _normalize_chara(data)
    except:
        return None

# -- Card Discovery ----------------------------------------
def discover_cards(search_dirs: list[Path]) -> list[dict]:
    cards = []
    seen = set()
    for d in search_dirs:
        if not d.exists():
            continue
        for p in sorted(d.iterdir()):
            if p.suffix.lower() == ".png":
                raw = read_png_chara(p)
                chara = _normalize_chara(raw)
                if chara:
                    key = chara.get("name", p.stem)
                    if key not in seen:
                        seen.add(key)
                        cards.append({"name": key, "source": str(p), "type": "png", "data": chara})
            elif p.suffix.lower() == ".json":
                chara = read_json_chara(p)
                if chara and chara.get("name"):
                    key = chara["name"]
                    if key not in seen:
                        seen.add(key)
                        cards.append({"name": key, "source": str(p), "type": "json", "data": chara})
        # subdirectories
        for sub in d.iterdir():
            if not sub.is_dir():
                continue
            for p in sorted(sub.glob("*.png")):
                if p.name.startswith("thumbnail") or p.name.startswith("._"):
                    continue
                raw = read_png_chara(p)
                chara = _normalize_chara(raw)
                if chara:
                    key = chara.get("name", f"{sub.name}/{p.stem}")
                    if key not in seen:
                        seen.add(key)
                        cards.append({"name": key, "source": str(p), "type": "png_subdir", "data": chara})
    return cards

def discover_harem() -> list[dict]:
    members = []
    if not HAREM_DIR.exists():
        return members
    for d in sorted(HAREM_DIR.iterdir()):
        if not d.is_dir():
            continue
        soul = d / "SOUL.md"
        identity = d / "IDENTITY.md"
        if soul.exists():
            members.append({"name": d.name, "dir": str(d), "has_soul": True, "has_identity": identity.exists()})
    return members

# -- Identify current active character ---------------------
def get_active_character() -> Optional[str]:
    """Returns the harem key of the currently active character."""
    soul = WORKSPACE_ROOT / "SOUL.md"
    if not soul.exists():
        return None
    with open(soul, "r", encoding="utf-8") as f:
        first = f.readline().strip()
    # Try exact match from SOUL.md title
    m = re.match(r"^# SOUL\.md\s*-\s*(.+)$", first)
    display_name = m.group(1).strip() if m else None
    # Match against harem dirs (compare SOUL.md content)
    harem = discover_harem()
    current_hash = soul.read_bytes()
    for h in harem:
        h_soul = HAREM_DIR / h["name"] / "SOUL.md"
        if h_soul.exists() and h_soul.read_bytes() == current_hash:
            return h["name"]
    # Fallback: display name
    return display_name

# -- Parse character data ----------------------------------
def parse_chara_description(data: dict) -> dict:
    desc = data.get("description", "")
    personality = data.get("personality", "")
    full_text = desc or ""

    result = {
        "name": data.get("name", "Unknown"),
        "appearance": "",
        "personality": personality or "",
        "background": "",
        "notes": "",
        "greeting": data.get("first_mes", "Hello."),
        "scenario": data.get("scenario", ""),
        "mes_example": data.get("mes_example", ""),
        "system_prompt": data.get("system_prompt", ""),
        "raw_description": full_text,
    }

    section_patterns = [
        (r"<[Aa]ppearance[^>]*>(.+?)(?=</?[A-Za-z]|$)", "appearance"),
        (r"<[Pp]ersonality[^>]*>(.+?)(?=</?[A-Za-z]|$)", "personality"),
        (r"<[Bb]ackground[^>]*>(.+?)(?=</?[A-Za-z]|$)", "background"),
        (r"<[Gg]eneral[_ ]?[Dd]escription[^>]*>(.+?)(?=</?[A-Za-z]|$)", "notes"),
    ]
    for pattern, key in section_patterns:
        m = re.search(pattern, full_text, re.DOTALL)
        if m and not result.get(key):
            result[key] = m.group(1).strip()

    if not result["personality"]:
        m = re.search(
            r"(?:Personality|性格|人设)[:：]\s*(.{20,500}?)(?:\n\n|\n(?=[A-Z\u4e00-\u9fff]{2,10}[:：])|$)",
            full_text, re.DOTALL,
        )
        if m:
            result["personality"] = m.group(1).strip()

    if not result["personality"]:
        result["personality"] = full_text[:2000] if full_text else ""

    return result

def normalize_chara_name(name: str) -> str:
    name = Path(name).name
    name = re.sub(r"[<>:\"/\\|?*]", "", name)
    name = name.strip()
    return name

# -- Write role files --------------------------------------
def write_soul_md(parsed: dict, output_dir: Path):
    name = parsed["name"]
    lines = [f"# SOUL.md - {name}", "", f"**角色设定：** {name}，{parsed.get('background', '来自异世界的访客。')[:100]}", ""]
    for key, heading in [("personality", "性格"), ("appearance", "外貌"), ("background", "背景设定"), ("notes", "备注"), ("scenario", "与你的关系")]:
        val = parsed.get(key, "")
        if val:
            lines.append(f"## {heading}")
            lines.append("")
            for para in val.split("\n"):
                para = para.strip()
                if para:
                    lines.append(f"* {para}" if not para.startswith("*") else para)
            lines.append("")
    (output_dir / "SOUL.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"  Wrote {output_dir / 'SOUL.md'}")

def write_identity_md(parsed: dict, output_dir: Path):
    name = parsed["name"]
    lines = [
        f"# IDENTITY.md",
        "",
        f"* **Name:** {name}",
        f"* **Creature:** 角色扮演",
        f"* **Vibe:** {parsed.get('personality', '')[:80]}",
        f"* **Emoji:** 随意",
        "",
        f"扮演 {name}。按照 SOUL.md 中设定的性格行事。",
    ]
    (output_dir / "IDENTITY.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"  Wrote {output_dir / 'IDENTITY.md'}")

# -- Save current character to harem -----------------------
def save_current_to_harem():
    active = get_active_character()
    if not active:
        print("  [!] No active character detected, skipping backup")
        return None
    safe = normalize_chara_name(active).lower().replace(" ", "-")
    dest = HAREM_DIR / safe
    dest.mkdir(parents=True, exist_ok=True)
    for fname in ROOT_FILES:
        src = WORKSPACE_ROOT / fname
        if src.exists():
            shutil.copy2(src, dest / fname)
    print(f"  Saved '{active}' -> harem/{safe}/")
    return safe

# -- Switch to character -----------------------------------
def do_switch(parsed: dict, source_name: str):
    """Switch active character: save current -> harem, write new to root + workspace."""
    # Save current
    old_key = save_current_to_harem()

    name = parsed["name"]
    safe = normalize_chara_name(name).lower().replace(" ", "-")

    # Write to harem
    harem_dest = HAREM_DIR / safe
    harem_dest.mkdir(parents=True, exist_ok=True)
    write_soul_md(parsed, harem_dest)
    write_identity_md(parsed, harem_dest)

    # Copy to workspace root (D:\AI_Girlfriend)
    for fname in ROOT_FILES:
        shutil.copy2(harem_dest / fname, WORKSPACE_ROOT / fname)

    # Also sync to active OpenClaw workspace
    if OPENCLAW_WS.exists():
        for fname in ROOT_FILES:
            shutil.copy2(harem_dest / fname, OPENCLAW_WS / fname)
        print(f"  Synced to {OPENCLAW_WS}")

    # Ensure role_play subdir exists
    mem_dir = ROLE_MEMORY_DIR / safe
    mem_dir.mkdir(parents=True, exist_ok=True)

    # 切换 TTS 权重
    _switch_tts_weights(safe)

    print(f"\n[OK] Switched to '{name}'!")
    print(f"     Role: skills/harem/{safe}/")
    print(f"     Memory: memory/role_play/{safe}/")
    print(f"     Previous '{old_key}' saved to harem.")
    print(f"     Run /reset to reload.")


def do_switch_harem(name: str):
    """Switch to an existing harem member by name."""
    safe = normalize_chara_name(name).lower().replace(" ", "-")
    src = HAREM_DIR / safe
    if not src.exists() or not (src / "SOUL.md").exists():
        print(f"[X] Harem member '{name}' not found in {src}")
        members = discover_harem()
        if members:
            print(f"  Available: {', '.join(m['name'] for m in members)}")
        return

    # Save current
    old_key = save_current_to_harem()

    # Copy from harem to root
    for fname in ROOT_FILES:
        sf = src / fname
        if sf.exists():
            shutil.copy2(sf, WORKSPACE_ROOT / fname)

    # Sync to workspace
    if OPENCLAW_WS.exists():
        for fname in ROOT_FILES:
            sf = src / fname
            if sf.exists():
                shutil.copy2(sf, OPENCLAW_WS / fname)

    # 切换 TTS 权重
    _switch_tts_weights(safe)

    print(f"\n[OK] Switched to '{name}' from harem!")
    print(f"     Previous '{old_key}' saved.")
    print(f"     Run /reset to reload.")


# -- Commands ---------------------------------------------
def cmd_list(args):
    # Cards
    search_dirs = []
    if args.dir:
        search_dirs.append(Path(args.dir))
    if args.st_dir:
        search_dirs.append(Path(args.st_dir))
    if CARDS_DIR.exists():
        search_dirs.append(CARDS_DIR)

    cards = discover_cards(search_dirs)
    harem = discover_harem()
    active = get_active_character()

    print(f"\n{'='*65}")
    if active:
        print(f"  * Active: {active}")
    else:
        print(f"  * Active: (none)")

    # Harem
    if harem:
        print(f"\n  -- Harem ({len(harem)} members) --")
        for h in harem:
            marker = " <-- ACTIVE" if h["name"] == active or h["name"].lower() == (active or "").lower() else ""
            print(f"  [{h['name']}]{marker}")
        print(f"\n  Switch: python card_importer.py switch-harem <name>")

    # Cards
    if cards:
        print(f"\n  -- Character Cards ({len(cards)} available) --")
        for c in cards:
            print(f"  [{c['name']}] {c['source']}")
        print(f"\n  Switch: python card_importer.py switch \"<path>\"")

    if not cards and not harem:
        print("  No characters found.")
    print(f"{'='*65}")


def cmd_preview(args):
    path = Path(args.path)
    if not path.exists():
        print(f"[X] Not found: {path}")
        return
    if path.suffix.lower() == ".png":
        raw = read_png_chara(path)
        chara = _normalize_chara(raw)
    elif path.suffix.lower() == ".json":
        chara = read_json_chara(path)
    else:
        print(f"[X] Unsupported: {path.suffix}")
        return
    if not chara:
        print(f"[X] No character data in {path.name}")
        return
    parsed = parse_chara_description(chara)
    _print_parsed(parsed)


def cmd_switch(args):
    """Switch to a ST character card. Saves current to harem first."""
    path = Path(args.path)
    if not path.exists():
        print(f"[X] Not found: {path}")
        return
    if path.suffix.lower() == ".png":
        raw = read_png_chara(path)
        chara = _normalize_chara(raw)
    elif path.suffix.lower() == ".json":
        chara = read_json_chara(path)
    else:
        print(f"[X] Unsupported: {path.suffix}")
        return
    if not chara:
        print(f"[X] No character data in {path.name}")
        return

    parsed = parse_chara_description(chara)
    name = parsed["name"]
    print(f"\n{'='*50}")
    print(f"  Switching to: {name}")
    print(f"  Source: {path}")
    print(f"{'='*50}")
    _print_parsed(parsed)

    if not args.force:
        resp = input(f"\n  Switch to '{name}'? Current character will be saved to harem. [y/N]: ").strip().lower()
        if resp not in ("y", "yes"):
            print("  Cancelled.")
            return

    do_switch(parsed, path.name)


def cmd_switch_harem(args):
    """Switch to a harem member."""
    active = get_active_character()
    if active and active.lower() == args.name.lower():
        print(f"  '{args.name}' is already active.")
        return
    do_switch_harem(args.name)


def _print_parsed(parsed: dict):
    print(f"\n  * {parsed['name']}")
    print(f"  {'-'*50}")
    for key, label in [
        ("personality", "Personality"),
        ("appearance", "Appearance"),
        ("background", "Background"),
        ("scenario", "Scenario"),
        ("greeting", "First Message"),
    ]:
        val = parsed.get(key, "")
        if val:
            val_clean = re.sub(r"<[^>]+>", "", val).strip()[:300]
            print(f"\n  -- {label} --")
            for line in val_clean.split("\n")[:6]:
                line = line.strip()
                if line:
                    print(f"  {line}")


# -- Chat Import ------------------------------------------
def discover_chats(chats_dir: Path, chara_name: str = None) -> list[dict]:
    chats = []
    if not chats_dir.exists():
        return chats
    for chara_dir in sorted(chats_dir.iterdir()):
        if not chara_dir.is_dir():
            continue
        if chara_name and chara_name.lower() not in chara_dir.name.lower():
            continue
        for f in sorted(chara_dir.glob("*.jsonl")):
            stat = f.stat()
            chats.append({"character": chara_dir.name, "path": str(f), "size": stat.st_size, "mtime": stat.st_mtime, "filename": f.name})
    return chats

def parse_jsonl_messages(jsonl_path: Path) -> tuple[list[dict], str, str]:
    messages, chara_name, user_name = [], "Assistant", "User"
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "chat_metadata" in msg:
                continue
            if msg.get("name"):
                nm = msg["name"]
                if msg.get("is_user"):
                    user_name = nm
                else:
                    chara_name = nm
            mes = msg.get("mes", "")
            if not mes:
                continue
            mes_clean = re.sub(r"<[^>]+>", "", mes)
            mes_clean = re.sub(r"\r\n", "\n", mes_clean)
            mes_clean = re.sub(r"\n{3,}", "\n\n", mes_clean)
            mes_clean = re.sub(r"<think>.*?</think>", "", mes_clean, flags=re.DOTALL).strip()
            if not mes_clean:
                continue
            messages.append({"is_user": msg.get("is_user", False), "name": msg.get("name", user_name if msg.get("is_user") else chara_name), "mes": mes_clean, "send_date": msg.get("send_date", "")})
    return messages, chara_name, user_name

def format_roleplay_markdown(messages: list[dict], chara_name: str, user_name: str, title: str = "", scenario: str = "") -> str:
    date_str = "unknown-date"
    if messages:
        try:
            dt = datetime.fromisoformat(messages[0]["send_date"].replace("Z", "+00:00"))
            date_str = dt.strftime("%Y-%m-%d")
        except:
            pass
    lines = [f"# {date_str} -- {title or chara_name}", ""]
    if scenario:
        lines.append("## Scenario")
        lines.append(scenario.strip())
        lines.append("")
    lines.append("## Chat Log (imported from SillyTavern)")
    lines.append("")
    segment_idx, last_is_user = 1, None
    for i, msg in enumerate(messages):
        is_user = msg["is_user"]
        speaker = user_name if is_user else chara_name
        mes = msg["mes"]
        time_str = ""
        try:
            dt = datetime.fromisoformat(msg["send_date"].replace("Z", "+00:00"))
            time_str = dt.strftime(" (%H:%M)")
        except:
            pass
        if is_user and (last_is_user is not True):
            lines.append(f"### {segment_idx}.{time_str}")
            segment_idx += 1
        elif not is_user and last_is_user is True:
            lines.append(f"### {segment_idx}.{time_str}")
            segment_idx += 1
        prefix = f"- **{speaker}**: "
        for para in mes.split("\n\n"):
            para = para.strip()
            if not para:
                continue
            lines.append(f"{prefix}{para}")
            prefix = "  "
        lines.append("")
        last_is_user = is_user
    lines.append("---")
    lines.append(f"*Imported from SillyTavern chat with {chara_name}*")
    return "\n".join(lines)

def cmd_list_chats(args):
    chats_dir = Path(args.chats_dir) if args.chats_dir else ST_CHATS_DIR
    chats = discover_chats(chats_dir, args.character)
    if not chats:
        print(f"No chat logs found in {chats_dir}")
        return
    print(f"\n{'-'*70}")
    print(f"  Found {len(chats)} chat log(s)")
    print()
    for i, c in enumerate(chats, 1):
        size_kb = c["size"] / 1024
        mtime = datetime.fromtimestamp(c["mtime"]).strftime("%Y-%m-%d %H:%M")
        print(f"  [{i}] {c['character']:30s} | {c['filename'][:50]:50s} | {size_kb:6.1f} KB | {mtime}")
    print(f"{'-'*70}")

def cmd_import_chat(args):
    jsonl_path = Path(args.path)
    if not jsonl_path.exists():
        print(f"[X] Not found: {jsonl_path}")
        return
    print(f"\nReading: {jsonl_path.name}")
    messages, chara_name, user_name = parse_jsonl_messages(jsonl_path)
    if not messages:
        print("[X] No messages found.")
        return
    user_msgs = sum(1 for m in messages if m["is_user"])
    print(f"  {len(messages)} messages ({user_msgs} user, {len(messages)-user_msgs} {chara_name})")
    for m in messages[:3]:
        snippet = m["mes"][:100].replace("\n", " ")
        print(f"    [{m['name']}] {snippet}...")

    # Which character subdir?
    safe = normalize_chara_name(chara_name).lower().replace(" ", "-")
    title = args.title if args.title else chara_name
    if not args.force:
        t = input(f"\n  Memory title [{title}]: ").strip()
        if t:
            title = t
        s = input(f"  Scenario (optional): ").strip()
        scenario = s
    else:
        scenario = args.scenario if args.scenario else ""

    try:
        dt = datetime.fromisoformat(messages[0]["send_date"].replace("Z", "+00:00"))
        date_str = dt.strftime("%Y-%m-%d")
    except:
        date_str = "unknown"

    filename = f"{date_str}-{safe}.md"
    out_dir = ROLE_MEMORY_DIR / safe
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename

    if out_path.exists() and not args.force:
        resp = input(f"  [!] {out_path.name} exists. Overwrite? [y/N]: ").strip().lower()
        if resp not in ("y", "yes"):
            print("  Cancelled.")
            return

    md = format_roleplay_markdown(messages, chara_name, user_name, title, scenario)
    out_path.write_text(md, encoding="utf-8")
    print(f"\n[OK] Imported {len(messages)} messages -> {out_path}")


# -- CLI --------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Harem Manager - ST Card Importer for AI Girlfriend")
    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="List all cards + harem members")
    p_list.add_argument("--dir", help="Custom search directory")
    p_list.add_argument("--st-dir", default=str(ST_CHARACTERS_DIR) if ST_CHARACTERS_DIR else None)

    p_preview = sub.add_parser("preview", help="Preview a character card")
    p_preview.add_argument("path")

    p_switch = sub.add_parser("switch", help="Switch to a ST character card (saves current to harem)")
    p_switch.add_argument("path")
    p_switch.add_argument("--force", "-f", action="store_true")

    p_sh = sub.add_parser("switch-harem", help="Switch to an existing harem member")
    p_sh.add_argument("name")

    p_lc = sub.add_parser("list-chats", help="List ST chat logs")
    p_lc.add_argument("--chats-dir", default=str(ST_CHATS_DIR) if ST_CHATS_DIR else None)
    p_lc.add_argument("--character", "-c")

    p_ic = sub.add_parser("import-chat", help="Import ST chat JSONL to role_play")
    p_ic.add_argument("path")
    p_ic.add_argument("--force", "-f", action="store_true")
    p_ic.add_argument("--title", "-t")
    p_ic.add_argument("--scenario", "-s")

    args = parser.parse_args()

    if args.command == "list":
        cmd_list(args)
    elif args.command == "preview":
        cmd_preview(args)
    elif args.command == "switch":
        cmd_switch(args)
    elif args.command == "switch-harem":
        cmd_switch_harem(args)
    elif args.command == "list-chats":
        cmd_list_chats(args)
    elif args.command == "import-chat":
        cmd_import_chat(args)
    else:
        parser.print_help()
        print("\nQuick start:")
        print("  python card_importer.py list")
        print("  python card_importer.py switch \"cards/Enola.png\" --force")
        print("  python card_importer.py switch-harem natsume")
        print("  python card_importer.py import-chat \"path/to/chat.jsonl\" --force")


if __name__ == "__main__":
    main()
