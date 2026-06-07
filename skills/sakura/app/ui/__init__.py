"""桌宠 UI 组件包。"""

from app.ui.frosted_glass_frame import FrostedGlassFrame
from app.ui.manual_screenshot_overlay import (
    MANUAL_SCREENSHOT_MIN_SIZE,
    ManualScreenshotOverlay,
)
from app.ui.portrait_controller import PortraitController
from app.ui.screen_capture import capture_virtual_desktop_pixmap
from app.ui.styles import PET_WINDOW_STYLEHEET
from app.ui.subtitle_controller import SubtitleController
from app.ui.tool_confirmation_panel import ToolConfirmationPanel
from app.ui.tray_menu import build_pet_tray_menu

__all__ = [
    "FrostedGlassFrame",
    "MANUAL_SCREENSHOT_MIN_SIZE",
    "ManualScreenshotOverlay",
    "PortraitController",
    "capture_virtual_desktop_pixmap",
    "PET_WINDOW_STYLEHEET",
    "SubtitleController",
    "ToolConfirmationPanel",
    "build_pet_tray_menu",
]
