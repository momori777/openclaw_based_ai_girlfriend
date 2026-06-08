"""Resolve Claude Desktop data directories across installation types.

When Claude Desktop is installed as a Windows Package App (MSIX, e.g. via
Microsoft Store), Windows virtualizes ``%APPDATA%`` into a per-package
location::

    %LOCALAPPDATA%\\Packages\\<PackageFamilyName>\\LocalCache\\Roaming\\Claude

The standard (non-packaged) installation uses::

    %APPDATA%\\Claude

This module probes both locations and returns the first one that exists.
"""

from pathlib import Path
import glob
import logging
import os

logger = logging.getLogger(__name__)

# Known MSIX package-family prefix for Claude Desktop.  The suffix after the
# underscore is a publisher-id hash that is stable across versions.
_CLAUDE_PACKAGE_PREFIX = "Claude_"


def get_claude_data_dir() -> Path | None:
    """Return the Claude Desktop data directory, or ``None`` if not found.

    Resolution order:

    1. **MSIX path** - ``%LOCALAPPDATA%\\Packages\\Claude_*\\LocalCache\\Roaming\\Claude``
    2. **Standard path** - ``%APPDATA%\\Claude``

    Returns ``None`` when neither location exists (Claude may not be installed).
    """
    msix_dir = _find_msix_claude_dir()
    if msix_dir is not None:
        logger.info("Detected MSIX Claude Desktop data dir: %s", msix_dir)
        return msix_dir

    standard_dir = _find_standard_claude_dir()
    if standard_dir is not None:
        logger.info("Detected standard Claude Desktop data dir: %s", standard_dir)
        return standard_dir

    logger.debug("Claude Desktop data directory not found")
    return None


def get_claude_config_path() -> Path | None:
    """Return the path to ``claude_desktop_config.json``, or ``None``."""
    data_dir = get_claude_data_dir()
    if data_dir is None:
        return None
    config_path = data_dir / "claude_desktop_config.json"
    return config_path if config_path.is_file() else None


def is_msix_install() -> bool:
    """Return ``True`` if Claude Desktop appears to be an MSIX installation."""
    return _find_msix_claude_dir() is not None


def _find_msix_claude_dir() -> Path | None:
    """Probe ``%LOCALAPPDATA%\\Packages`` for a Claude MSIX package directory."""
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        return None

    packages_dir = Path(local_appdata) / "Packages"
    if not packages_dir.is_dir():
        return None

    # Match directories like Claude_pzs8sxrjxfjjc (the publisher-id suffix
    # varies, so we use a glob).
    pattern = str(packages_dir / f"{_CLAUDE_PACKAGE_PREFIX}*")
    for match in glob.glob(pattern):
        candidate = Path(match) / "LocalCache" / "Roaming" / "Claude"
        if candidate.is_dir():
            return candidate

    return None


def _find_standard_claude_dir() -> Path | None:
    """Probe ``%APPDATA%\\Claude`` for a standard (non-MSIX) install."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None

    candidate = Path(appdata) / "Claude"
    return candidate if candidate.is_dir() else None
