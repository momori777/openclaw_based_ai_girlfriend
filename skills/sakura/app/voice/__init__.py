"""语音播放相关控制器。"""

from app.voice.playback_controller import VoicePlaybackController
# TTS 类延迟导入，避免缺少音频库时阻塞整个 voice 包
# from app.voice.tts import GenieTTSProvider, GPTSoVITSTTSProvider, GPTSoVITSTTSSettings, NullTTSProvider, TTSConfigError, TTSProvider

__all__ = [
    "GenieTTSProvider",
    "GPTSoVITSTTSProvider",
    "GPTSoVITSTTSSettings",
    "NullTTSProvider",
    "TTSConfigError",
    "TTSProvider",
    "VoicePlaybackController",
]
