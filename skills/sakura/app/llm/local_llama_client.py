"""
本地 llama-server 后端适配器。

设计目标（与 TTS/ComfyUI 保持一致的生命周期管理模式）：
- 默认指向 localhost:8080/v1 (llama-server, Qwen3.6-35B)
- llama 被 TTS/ComfyUI 杀死时：停止发请求，轮询等待 llama 重启就绪
- 检测到 llama 重启完成（/health 200 → /completion 响应）后自动恢复
- 不在等待期间盲目重试浪费调用栈
- 支持远程 API fallback（若 llama 永久不可用）

这是 Sakura Desktop Pet 与本地 AI_Girlfriend 项目的 LLM 共享层。
三个 skill 共一颗大脑——Sakura 不做杀/启操作，只做"感知恢复"。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
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

# ── 内联 llama 工具（原 llama_utils.py 编码损坏，内联避免依赖） ──
from app.llm.llama_utils_inline import (
    detect_llama_unavailable,
    port_open,
    wait_for_llama_ready,
)


# ── 配置常量 ──────────────────────────────────────────────────
_LOCALHOST_BASE_URL = "http://localhost:8080/v1"
_LOCAL_MODEL_DEFAULT = "qwen3.6-35b"
_LLAMA_PORT = 8080

# llama 重启等待超时（单位：秒）
# TTS 推理 ~30s + llama 重载 ~15s → 给足 300s
_LLAMA_WAIT_TIMEOUT = 300


@dataclass
class LocalLlamaConfig:
    """本地 llama 后端配置。"""

    base_url: str = _LOCALHOST_BASE_URL
    model: str = _LOCAL_MODEL_DEFAULT
    fallback_base_url: str = ""
    fallback_model: str = ""
    timeout_seconds: int = 120
    api_key: str = "local"


class LocalLlamaClient:
    """带 llama 生命周期感知的 LLM 客户端。

    核心机制（与 TTS/ComfyUI 保持一致）：
    1. 发 LLM 请求 → 检测到 llama 被 TTS/ComfyUI kill
    2. 停止发请求，进入"等待恢复"状态
    3. 轮询 /health + /completion，检测到 llama 就绪
    4. 自动恢复，重新发请求

    不做的事（与 TTS/ComfyUI 不同）：
    - 不会自己 kill llama
    - 不会自己 restart llama
    - 只感知外部生命周期事件
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
        self._llama_available = True

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

    # ── LLM 方法（全部走 _with_llama_sense） ─────────────────

    def chat(
        self,
        system_prompt: str,
        messages: list[ChatMessage],
        reply_tones: list[str] | None = None,
        reply_portraits: list[str] | None = None,
    ) -> ChatReply:
        return self._with_llama_sense(
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
        return self._with_llama_sense(
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
        return self._with_llama_sense(
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

    # ── 核心生命周期感知逻辑 ──────────────────────────────────

    def _with_llama_sense(self, method_name: str, operation: Any) -> Any:
        """执行 LLM 操作，带 llama 生命周期感知。

        逻辑：
        1. 如果 llama 可用 → 直接发请求
        2. 如果请求失败且是 "llama 不可用" 错误 → 进入等待恢复模式
        3. 等待模式：停止发请求，轮询 /health + /completion
        4. llama 就绪 → 自动恢复，立即重新发请求
        5. 超时或 fallback 已配置 → 使用 fallback

        不做的事：
        - 不会自己 kill/restart llama（那是 TTS/ComfyUI 的职责）
        - 不会在等待期间盲目重试
        """
        if not self._llama_available and self._fallback_client:
            debug_log(
                "LocalLlama",
                f"llama 不可用，使用 fallback → {method_name}",
            )
            return operation(self._fallback_client)

        # 尝试本地 llama
        try:
            result = operation(self._primary_client)
            if not self._llama_available:
                debug_log("LocalLlama", "llama 已恢复，切回本地")
                self._llama_available = True
            return result
        except ApiRequestError as exc:
            if not detect_llama_unavailable(exc):
                raise  # 不是 llama 掉线的错误，正常抛出

            # llama 被 TTS/ComfyUI 杀了 → 进入等待恢复模式
            self._llama_available = False
            debug_log(
                "LocalLlama",
                "llama 不可用（被 TTS/ComfyUI 暂时杀死），进入等待恢复模式...",
                {"error": str(exc)[:200]},
            )

            # 等待 llama 重启就绪（使用共享模块三阶段验证）
            if wait_for_llama_ready(
                port=_LLAMA_PORT,
                timeout=_LLAMA_WAIT_TIMEOUT,
                log=lambda msg: debug_log("LocalLlama", msg),
            ):
                debug_log("LocalLlama", "llama 恢复就绪，重试请求")
                self._llama_available = True
                # 立即重新发请求
                return operation(self._primary_client)

            # 超时 → 尝试 fallback
            if self._fallback_client:
                debug_log(
                    "LocalLlama",
                    f"llama 恢复超时（{_LLAMA_WAIT_TIMEOUT}s），切换到 fallback → {method_name}",
                )
                return operation(self._fallback_client)

            raise ApiRequestError(
                f"本地 llama 在 {_LLAMA_WAIT_TIMEOUT}s 内未恢复。"
            )

    def set_fallback(
        self, base_url: str, model: str, api_key: str = "", timeout: int = 60
    ) -> None:
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
