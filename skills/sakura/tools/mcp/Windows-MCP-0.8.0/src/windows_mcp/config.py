import os


def is_debug() -> bool:
    """Return True if debug mode is enabled via the WINDOWS_MCP_DEBUG environment variable."""
    return os.getenv("WINDOWS_MCP_DEBUG", "false").lower() in ("1", "true", "yes", "on")


def enable_debug() -> None:
    """Enable debug mode by setting the WINDOWS_MCP_DEBUG environment variable."""
    os.environ["WINDOWS_MCP_DEBUG"] = "true"
