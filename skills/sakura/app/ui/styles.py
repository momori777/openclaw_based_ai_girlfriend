from __future__ import annotations

from app.ui.theme import DEFAULT_THEME_SETTINGS, ThemeSettings, build_pet_window_stylesheet


def pet_window_stylesheet(settings: ThemeSettings = DEFAULT_THEME_SETTINGS) -> str:
    return build_pet_window_stylesheet(settings)


PET_WINDOW_STYLEHEET = pet_window_stylesheet()
