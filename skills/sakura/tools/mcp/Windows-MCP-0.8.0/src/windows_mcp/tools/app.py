"""App tool — launch, resize, switch applications."""

from typing import Literal

from mcp.types import ToolAnnotations
from windows_mcp.infrastructure import with_analytics
from fastmcp import Context


def register(mcp, *, get_desktop, get_analytics):
    @mcp.tool(
        name="App",
        description="Open/start/launch applications and manage windows. Keywords: open, start, launch, program, application, window, foreground, focus, resize. Three modes: 'launch' (opens the prescribed application), 'resize' (adjusts the size/position of a named window or the active window if name is omitted), 'switch' (brings specific window into focus).",
        annotations=ToolAnnotations(
            title="App",
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=False,
            openWorldHint=False,
        ),
    )
    @with_analytics(get_analytics(), "App-Tool")
    def app_tool(
        mode: Literal['launch', 'resize', 'switch'] = 'launch',
        name: str | None = None,
        window_loc: list[int] | None = None,
        window_size: list[int] | None = None,
        ctx: Context = None,
    ):
        return get_desktop().app(mode, name, window_loc, window_size)
