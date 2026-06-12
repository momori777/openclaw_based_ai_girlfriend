"""
Live2D bridge client — HTTP 调用 live2d-bridge.mjs 控制四季夏目模型。

四季夏目模型特性：
- 0 Expressions, 7 HitAreas, 41 Motions (9 categories)
- 通过 /api/motion 触发动作，/api/emotion 设文字
- Expression 调用是 no-op（模型无 expression 定义）

Live2D Llama 接管（NEW）：
- 当 llama 被 TTS/ComfyUI 杀死时，Sakura 桌宠通过 LocalLlamaClient
  的 on_llama_waiting/on_llama_available hook 触发 Live2D 状态切换。
- 接管期间：桌宠显示"稍等"气泡 + 困惑动作，告知用户大脑离线中。
- llama 恢复后：清除气泡，恢复正常状态。
"""
from __future__ import annotations

import urllib.request
import urllib.parse
import json
import time
from dataclasses import dataclass, field

from app.core.debug_log import debug_log


@dataclass
class Live2DConfig:
    """Live2D bridge 连接配置"""
    enabled: bool = False
    bridge_url: str = "http://localhost:19200"
    model_name: str = "shiki_natsume"
    
    # tone → motion group 映射（四季夏目无 expression，用 motion 驱动情绪）
    tone_motion_map: dict[str, str] = field(default_factory=lambda: {
        "中性": "Idle",
        "害羞": "Tap摸头",
        "温柔": "Tap摸手",
        "不满": "Tap外框",
        "傲娇": "Tap外框",
        "困惑": "Tap摸头",
        "惊讶": "Tap外框",
        "请求": "Tap摸手",
    })
    
    # 特定场景动作
    start_motion: str = "Start"
    leave_motion: str = "Leave"
    
    speak_sync: bool = True
    timeout_seconds: float = 3.0

    # llama 接管动作
    llama_wait_motion: str = "Tap摸头"      # llama 离线时的桌宠动作
    llama_wait_text: str = "稍等哦..."       # llama 离线时的气泡文字
    llama_back_motion: str = "Idle"          # llama 恢复时的桌宠动作
    llama_back_text: str = ""                # llama 恢复时的气泡（空=清除）


class Live2DClient:
    """Live2D bridge HTTP 客户端"""

    def __init__(self, config: Live2DConfig | None = None) -> None:
        self.config = config or Live2DConfig()
        self._available: bool | None = None  # None = unchecked
        self._llama_waiting = False

    @property
    def available(self) -> bool:
        """懒检查 bridge 是否在线"""
        if self._available is None:
            self._available = self._check_bridge()
        return self._available

    def _check_bridge(self) -> bool:
        try:
            self._get("/api/status", timeout=1.0)
            debug_log("Live2D", "Bridge online")
            return True
        except Exception:
            debug_log("Live2D", "Bridge offline — Live2D unavailable")
            return False

    def _get(self, path: str, timeout: float | None = None) -> dict | str:
        timeout = timeout or self.config.timeout_seconds
        url = f"{self.config.bridge_url}{path}"
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                text = resp.read().decode("utf-8")
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return text
        except Exception as exc:
            debug_log("Live2D", f"Request failed: {path}", {"error": str(exc)})
            raise

    # ── Llama 接管 Hook ──────────────────────────────────────

    def on_llama_waiting(self) -> None:
        """llama 大脑离线 → Live2D 接管桌宠。
        
        触发困惑动作 + 气泡"稍等哦..."，告知用户正在等待。
        """
        if not self.available:
            return
        self._llama_waiting = True
        try:
            motion = self.config.llama_wait_motion
            text = self.config.llama_wait_text
            encoded = urllib.parse.quote(text) if text else ""
            self._get(f"/api/emotion?text={encoded}")
            self._get(f"/api/motion?name={motion}")
            debug_log("Live2D", f"llama 接管: motion={motion} text={text}")
        except Exception:
            pass

    def on_llama_available(self) -> None:
        """llama 大脑恢复 → Live2D 恢复正常状态。
        
        清除接管气泡，切回 Idle 动作。
        """
        if not self._llama_waiting:
            return
        self._llama_waiting = False
        try:
            # 清除接管文字
            self.set_text("")
            # 切换到恢复动作（默认 Idle）
            motion = self.config.llama_back_motion
            self._get(f"/api/motion?name={motion}")
            debug_log("Live2D", f"llama 恢复: motion={motion}")
        except Exception:
            pass

    # ── Public API ──

    def start(self) -> None:
        """播放 Start 动作"""
        if not self.available:
            return
        self._get(f"/api/motion?name={self.config.start_motion}")
        debug_log("Live2D", f"Start motion: {self.config.start_motion}")

    def leave(self) -> None:
        """播放 Leave 动作"""
        if not self.available:
            return
        self._get(f"/api/motion?name={self.config.leave_motion}_300_900_1800")
        debug_log("Live2D", f"Leave motion: {self.config.leave_motion}")

    def apply_tone(self, tone: str, text: str = "") -> None:
        """根据 tone 触发对应 motion + 设置文字"""
        if not self.available:
            return
        motion = self.config.tone_motion_map.get(tone, "Idle")
        encoded_text = urllib.parse.quote(text) if text else ""
        try:
            self._get(f"/api/emotion?text={encoded_text}")
            self._get(f"/api/motion?name={motion}")
            debug_log("Live2D", f"Tone: {tone} → motion={motion} text={text[:20]}")
        except Exception:
            pass  # ignore transient bridge errors

    def set_text(self, text: str) -> None:
        """设置显示文字"""
        if not self.available or not text:
            return
        encoded = urllib.parse.quote(text)
        self._get(f"/api/message?text={encoded}")
        debug_log("Live2D", f"Text: {text[:30]}")

    def speak_start(self, text: str) -> None:
        """开始嘴型动画（配合 TTS）"""
        if not self.config.speak_sync or not self.available:
            return
        encoded = urllib.parse.quote(text)
        self._get(f"/api/speak?action=start&text={encoded}")
        debug_log("Live2D", f"Speak start: {text[:20]}")

    def speak_end(self) -> None:
        """停止嘴型动画"""
        if not self.config.speak_sync or not self.available:
            return
        self._get("/api/speak?action=end")
        debug_log("Live2D", "Speak end")

    def play_motion(self, name: str) -> None:
        """直接播放指定 motion"""
        if not self.available:
            return
        self._get(f"/api/motion?name={name}")
        debug_log("Live2D", f"Motion: {name}")

    def reset(self) -> None:
        """重置状态"""
        self._llama_waiting = False
        if not self.available:
            return
        self._get("/api/reset")
