"""
本地 llama-server 后端适配器。

设计目标:
- 默认指向 localhost:8080/v1 (llama-server)
- llama 被 TTS/ComfyUI 暂时杀死时自动重试（指数退避，最长 90s）
- 检测到 "connection refused" 时不报错，静默等 llama 重启
- 支持 fallback 到远程 API（若本地 llama 长时间不可用）

这是 Sakura Desktop Pet 与本地 AI_Girlfriend 项目的 LLM 共享层。
"""

from __future__ import annotations

import time
import urllib.error
from dataclasses import dataclass, field
from typing import Any

from app.llm.api_client import (
    ApiRequestError,
    ApiSettings,
    ChatCompletionTurn,
    ChatMessage,
    OpenAICompatibleClient,
)
from app.llm.chat_reply import ChatReply
from app.core.debug_log import debug_log


_LOCALHOST_BASE_URL = "http://localhost:8080/v1"
_LOCAL_MODEL_DEFAULT = "qwen3.6-35b"

# 本地 llama 可能被 TTS/ComfyUI 暂时杀死（最长 ~90s）
# 指数退避: 2s, 4s, 8s, 16s, 32s, 64s → 总计 ~126s
_LLAMA_RETRY_BASE_DELAY = 2.0
_LLAMA_RETRY_MAX_DELAY = 64.0
_LLAMA_RETRY_MAX_ATTEMPTS = 6

# 检测 llama 不可用的错误特征
_LLAMA_UNAVAILABLE_MARKERS = (
    "connection refused",
    "connection reset",
    "refused",
    "timeout",
    "timed out",
    "500",
    "502",
    "503",
    "504",
    "no connection",
    "could not connect",
    "unreachable",
)


@dataclass
class LocalLlamaConfig:
    """本地 llama 后端配置。"""

    base_url: str = _LOCALHOST_BASE_URL
    model: str = _LOCAL_MODEL_DEFAULT
    fallback_base_url: str = ""
    fallback_model: str = ""
    timeout_seconds: int = 120
    api_key: str = "local"  # llama-server 不需要 key，但某些路径校验


def _detect_llama_unavailable(error: BaseException) -> bool:
    """判断错误是否由本地 llama 不可用（被 TTS/ComfyUI 杀死）引起。"""
    text = str(error).lower()
    return any(marker in text for marker in _LLAMA_UNAVAILABLE_MARKERS)


class LocalLlamaClient:
    """带 llama 生命周期感知的 LLM 客户端。

    当检测到 llama 被 TTS/ComfyUI 暂时杀死时，
    自动指数退避重试，直到 llama 重启完成。
    若超过最大重试次数，则切换 fallback 到远程 API。
    """

    def __init__(self, config: LocalLlamaConfig | None = None) -> None:
        self.config = config or LocalLlamaConfig()
        self._primary_settings = ApiSettings(
            base_url=self.config.base_url.rstrip("/"),
            api_key=self.config.api_key or "local",
            model=self.config.model,
            timeout_seconds=self.config.timeout_seconds,
        )
        self._primary_client = OpenAICompatibleClient(self._primary_settings)
        self._fallback_client: OpenAICompatibleClient | None = None
        self._llama_available = True  # 乐观假设
        self._last_llama_down_time = 0.0
        self._consecutive_failures = 0

    @property
    def is_using_local(self) -> bool:
        return self._llama_available

    def update_settings(self, settings: ApiSettings) -> None:
        """兼容 OpenAICompatibleClient 接口。"""
        self.config.model = settings.model
        self.config.base_url = settings.base_url.rstrip("/")
        self.config.timeout_seconds = settings.timeout_seconds
        self.config.api_key = settings.api_key
        self._primary_settings = ApiSettings(
            base_url=self.config.base_url.rstrip("/"),
            api_key=self.config.api_key or "local",
            model=self.config.model,
            timeout_seconds=self.config.timeout_seconds,
        )
        self._primary_client = OpenAICompatibleClient(self._primary_settings)

    def test_connection(self) -> str:
        if self._llama_available:
            try:
                return self._primary_client.test_connection()
            except ApiRequestError:
                pass
        if self._fallback_client:
            return self._fallback_client.test_connection()
        raise ApiRequestError("本地 llama 不可用，且未配置 fallback 远程 API。")

    def chat(
        self,
        system_prompt: str,
        messages: list[ChatMessage],
        reply_tones: list[str] | None = None,
        reply_portraits: list[str] | None = None,
    ) -> ChatReply:
        return self._with_llama_retry(
            "chat",
            lambda client: client.chat(
                system_prompt, messages,
                reply_tones=reply_tones,
                reply_portraits=reply_portraits,
            ),
        )

    def complete_raw(
        self,
        system_prompt: str,
        messages: list[ChatMessage],
        temperature: float = 0.8,
        **chat_params: Any,
    ) -> str:
        return self._with_llama_retry(
            "complete_raw",
            lambda client: client.complete_raw(
                system_prompt, messages,
                temperature=temperature,
                **chat_params,
            ),
        )

    def complete_with_tools(
        self,
        system_prompt: str,
        messages: list[ChatMessage],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = "auto",
        temperature: float = 0.8,
        structured_response: bool = False,
        **chat_params: Any,
    ) -> ChatCompletionTurn:
        return self._with_llama_retry(
            "complete_with_tools",
            lambda client: client.complete_with_tools(
                system_prompt, messages,
                tools=tools,
                tool_choice=tool_choice,
                temperature=temperature,
                structured_response=structured_response,
                **chat_params,
            ),
        )

    def list_models(self) -> list[str]:
        if self._llama_available:
            try:
                return self._primary_client.list_models()
            except ApiRequestError:
                pass
        if self._fallback_client:
            return self._fallback_client.list_models()
        return [self.config.model]

    # ── internal ──────────────────────────────────────────────

    def _with_llama_retry(self, method_name: str, operation: Any) -> Any:
        """执行 LLM 操作，带 llama 不可用自动重试和 fallback。

        当 llama 被 TTS/ComfyUI 杀死时：
        1. 指数退避重试（最多 6 次，最长 ~126s）
        2. 超过重试次数后切换 fallback 远程 API
        3. 重试成功时重置计数，重新标记 llama 可用
        """
        if not self._llama_available and self._fallback_client:
            debug_log(
                "LocalLlama",
                f"llama 不可用，直接使用 fallback",
                {"method": method_name},
            )
            return operation(self._fallback_client)

        # 本地 llama 路径
        for attempt in range(_LLAMA_RETRY_MAX_ATTEMPTS):
            try:
                result = operation(self._primary_client)
                # 成功 → 恢复可用标记
                if not self._llama_available:
                    debug_log(
                        "LocalLlama",
                        "llama 已恢复，切换回本地后端",
                        {"attempt": attempt + 1, "method": method_name},
                    )
                    self._llama_available = True
                self._consecutive_failures = 0
                return result
            except ApiRequestError as exc:
                if not _detect_llama_unavailable(exc):
                    raise  # 非 llama 不可用错误，直接抛出

                self._consecutive_failures += 1
                self._llama_available = False
                self._last_llama_down_time = time.monotonic()

                if attempt < _LLAMA_RETRY_MAX_ATTEMPTS - 1:
                    delay = min(
                        _LLAMA_RETRY_BASE_DELAY * (2 ** attempt),
                        _LLAMA_RETRY_MAX_DELAY,
                    )
                    debug_log(
                        "LocalLlama",
                        "llama 不可用（TTS/ComfyUI 可能正在运行），等待重试",
                        {
                            "attempt": attempt + 1,
                            "max_attempts": _LLAMA_RETRY_MAX_ATTEMPTS,
                            "delay_seconds": delay,
                            "error": str(exc),
                        },
                    )
                    time.sleep(delay)
                else:
                    # 所有重试都失败，尝试 fallback
                    if self._fallback_client:
                        debug_log(
                            "LocalLlama",
                            "本地 llama 长时间不可用，切换到远程 fallback",
                            {
                                "total_retries": _LLAMA_RETRY_MAX_ATTEMPTS,
                                "error": str(exc),
                            },
                        )
                        return operation(self._fallback_client)
                    raise

        raise ApiRequestError("本地 llama 长时间不可用。")

    def set_fallback(self, base_url: str, model: str, api_key: str = "", timeout: int = 60) -> None:
        """配置远程 fallback API（本地 llama 不可用时自动切换）。"""
        if not base_url or not model:
            self._fallback_client = None
            return
        self.config.fallback_base_url = base_url
        self.config.fallback_model = model
        settings = ApiSettings(
            base_url=base_url.rstrip("/"),
            api_key=api_key,
            model=model,
            timeout_seconds=timeout,
        )
        self._fallback_client = OpenAICompatibleClient(settings)
        debug_log(
            "LocalLlama",
            "远程 fallback 已配置",
            {"base_url": base_url, "model": model},
        )

    @staticmethod
    def create_default() -> LocalLlamaClient:
        """创建默认配置：本地 qwen3.6-35b，无 fallback。"""
        return LocalLlamaClient(LocalLlamaConfig())
