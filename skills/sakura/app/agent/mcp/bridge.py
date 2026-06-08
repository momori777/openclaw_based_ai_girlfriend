from __future__ import annotations

import asyncio
import shutil
import sys
import threading
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.agent.mcp.config import MCPServerConfig


@dataclass(frozen=True)
class MCPToolSpec:
    """MCP 工具元数据，供 Provider 转成 Sakura 内部 Tool。"""

    name: str
    description: str
    input_schema: dict[str, Any]


class MCPBridge:
    """同步封装官方 MCP 异步 ClientSession，便于现有工具线程调用。"""

    def __init__(self, config: MCPServerConfig, default_call_timeout: float) -> None:
        self.config = config
        self.default_call_timeout = default_call_timeout
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()
        self._closed = False
        self._connection_task: asyncio.Task[None] | None = None
        self._close_requested: asyncio.Event | None = None
        self._connect_error: BaseException | None = None
        self._session: Any | None = None

    def connect(self) -> None:
        if self._loop is not None:
            return
        self._ensure_stdio_command_exists()
        self._thread = threading.Thread(
            target=self._run_loop,
            name=f"sakura-mcp-{self.config.name}",
            daemon=True,
        )
        self._thread.start()
        if not self._ready.wait(timeout=5):
            raise TimeoutError(f"MCP Server {self.config.name} 事件循环启动超时。")
        self._run_async(self._connect(), timeout=self.config.effective_call_timeout(self.default_call_timeout))

    def list_tools(self) -> list[MCPToolSpec]:
        result = self._run_async(
            self._list_tools(),
            timeout=self.config.effective_call_timeout(self.default_call_timeout),
        )
        return result

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        timeout = self.config.effective_call_timeout(self.default_call_timeout)
        return self._run_async(self._call_tool(name, arguments), timeout=timeout)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._loop is None:
            return
        try:
            self._run_async(self._close_async(), timeout=5)
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread is not None:
                self._thread.join(timeout=5)
            self._loop = None
            self._thread = None

    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        self._ready.set()
        loop.run_forever()
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()

    def _run_async(self, coro: Any, timeout: float) -> Any:
        if self._loop is None:
            raise RuntimeError("MCP Bridge 尚未连接。")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    def _ensure_stdio_command_exists(self) -> None:
        """启动前检查 stdio 命令，避免把 WinError 2 直接暴露给用户。"""

        if self.config.transport != "stdio" or not self.config.command:
            return
        command = self.config.command.strip().strip('"').strip("'")
        if _stdio_command_exists(command):
            return
        raise RuntimeError(
            f"MCP Server {self.config.name} 启动失败：找不到命令 {command}。"
            "请先确认依赖已安装；如果这是 Windows MCP，请运行 install.bat 安装 uv，"
            "或在设置里关闭 Windows MCP 后重启 Sakura。"
        )

    async def _connect(self) -> None:
        ready = asyncio.Event()
        self._close_requested = asyncio.Event()
        self._connect_error = None
        self._connection_task = asyncio.create_task(self._connection_main(ready))
        await ready.wait()
        if self._connect_error is not None:
            raise self._connect_error

    async def _connection_main(self, ready: asyncio.Event) -> None:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.sse import sse_client
        from mcp.client.stdio import stdio_client

        stack = AsyncExitStack()
        try:
            if self.config.transport == "stdio":
                if not self.config.command:
                    raise ValueError(f"MCP Server {self.config.name} 缺少 command。")
                server_params = StdioServerParameters(
                    command=self.config.command,
                    args=self.config.args,
                    env=self.config.env or None,
                )
                read_stream, write_stream = await stack.enter_async_context(stdio_client(server_params))
            elif self.config.transport == "sse":
                if not self.config.url:
                    raise ValueError(f"MCP Server {self.config.name} 缺少 url。")
                read_stream, write_stream = await stack.enter_async_context(
                    sse_client(
                        self.config.url,
                        headers=self.config.headers or None,
                        timeout=self.config.effective_call_timeout(self.default_call_timeout),
                    )
                )
            else:
                raise ValueError(f"不支持的 MCP transport：{self.config.transport}")

            session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
            await session.initialize()
            self._session = session
            ready.set()
            close_requested = self._close_requested
            if close_requested is not None:
                await close_requested.wait()
        except Exception:
            self._connect_error = sys.exc_info()[1]
            ready.set()
            self._session = None
            raise
        finally:
            self._session = None
            await stack.aclose()

    async def _list_tools(self) -> list[MCPToolSpec]:
        session = self._require_session()
        response = await session.list_tools()
        tools = getattr(response, "tools", [])
        result: list[MCPToolSpec] = []
        for tool in tools:
            name = str(getattr(tool, "name", "")).strip()
            if not name:
                continue
            description = str(getattr(tool, "description", "") or "")
            schema = getattr(tool, "inputSchema", None) or getattr(tool, "input_schema", None) or {}
            result.append(
                MCPToolSpec(
                    name=name,
                    description=description,
                    input_schema=_as_json_object(schema),
                )
            )
        return result

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        session = self._require_session()
        result = await session.call_tool(name, arguments=arguments)
        return _format_call_tool_result(result)

    async def _close_async(self) -> None:
        if self._close_requested is not None:
            self._close_requested.set()
        if self._connection_task is not None:
            try:
                await self._connection_task
            except Exception:
                # 连接阶段已经报告过错误；关闭时只清理，避免二次刷屏。
                pass
        self._connection_task = None
        self._close_requested = None
        self._session = None

    def _require_session(self) -> Any:
        if self._session is None:
            raise RuntimeError("MCP Server 尚未连接。")
        return self._session


def _format_call_tool_result(result: Any) -> dict[str, Any]:
    structured = (
        getattr(result, "structuredContent", None)
        if hasattr(result, "structuredContent")
        else getattr(result, "structured_content", None)
    )
    content = getattr(result, "content", [])
    content_items = [_to_jsonable(item) for item in content] if isinstance(content, list) else []
    image_data_urls = _extract_image_data_urls(content_items)
    redacted_content_items = [_redact_content_image(item) for item in content_items]
    text_items = [
        str(item.get("text"))
        for item in redacted_content_items
        if isinstance(item, dict) and isinstance(item.get("text"), str)
    ]
    payload: dict[str, Any] = {
        "content": redacted_content_items,
        "is_error": bool(getattr(result, "isError", False) or getattr(result, "is_error", False)),
    }
    if structured is not None:
        payload["structured_content"] = _to_jsonable(structured)
    if text_items:
        payload["text"] = "\n".join(text_items)
    if image_data_urls:
        payload["mcp_image_data_urls"] = image_data_urls
        payload["screenshot_data_url"] = image_data_urls[0]
    return payload


def _as_json_object(value: Any) -> dict[str, Any]:
    data = _to_jsonable(value)
    return data if isinstance(data, dict) else {}


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=True, exclude_none=True)
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _extract_image_data_urls(value: Any) -> list[str]:
    images: list[str] = []
    if isinstance(value, dict):
        image_url = _image_item_to_data_url(value)
        if image_url is not None:
            images.append(image_url)
        for item in value.values():
            images.extend(_extract_image_data_urls(item))
    elif isinstance(value, list):
        for item in value:
            images.extend(_extract_image_data_urls(item))
    return _deduplicate_preserving_order(images)


def _redact_content_image(value: Any) -> Any:
    if isinstance(value, dict):
        if _image_item_to_data_url(value) is not None:
            return {
                "type": value.get("type", "image"),
                "image_attached": True,
                "mime_type": _image_mime_type(value),
            }
        return {str(key): _redact_content_image(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_content_image(item) for item in value]
    return value


def _image_item_to_data_url(item: dict[str, Any]) -> str | None:
    if str(item.get("type", "")).lower() != "image":
        return None
    data = item.get("data")
    if not isinstance(data, str) or not data.strip():
        return None
    if data.startswith("data:image/"):
        return data
    mime_type = _image_mime_type(item)
    if not mime_type.startswith("image/"):
        return None
    return f"data:{mime_type};base64,{data}"


def _image_mime_type(item: dict[str, Any]) -> str:
    mime_type = item.get("mimeType")
    if not isinstance(mime_type, str) or not mime_type.strip():
        mime_type = item.get("mime_type")
    if not isinstance(mime_type, str) or not mime_type.strip():
        mime_type = "image/png"
    return mime_type.strip()


def _deduplicate_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _stdio_command_exists(command: str) -> bool:
    if not command:
        return False
    if any(separator in command for separator in ("/", "\\")) or Path(command).is_absolute():
        return Path(command).is_file()
    return shutil.which(command) is not None
