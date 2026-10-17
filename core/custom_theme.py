"""
User-editable custom theme.

Stores a full palette (matching the keys used in PALETTES) in QSettings
under "custom_theme/<key>". When the user has never edited it, we fall
back to a sane default (based on the current built-in purple palette).

Exposes:
    CUSTOM_THEME_ID            — the string id "custom"
    load_custom_palette()      — dict of colors (or None if not customized)
    save_custom_palette(dict)  — persist
    reset_custom_palette()     — wipe, fall back to default
    has_custom_palette()       — bool
    default_custom_palette()   — the initial palette values
    random_palette()           — generate a random harmonious palette
    randomize_custom_palette() — generate + save + return
"""

from __future__ import annotations

import colorsys
import random

from PyQt6.QtCore import QSettings


CUSTOM_THEME_ID = "custom"

_KEYS = [
    "bg_root", "bg_panel", "bg_input",
    "bg_button", "bg_button_hover",
    "accent", "accent_dim", "accent_text",
    "ok", "ok_hover", "danger", "danger_hover", "warn",
    "text", "text_dim", "text_muted",
    "border", "border_focus",
    "tx_prefix", "tx_text",
]


def default_custom_palette() -> dict[str, str]:
    """Copy of the built-in 'purple' palette as a starting point."""
    return {
        "bg_root":         "#1a1225",
        "bg_panel":        "#241833",
        "bg_input":        "#2c1e3f",
        "bg_button":       "#36264b",
        "bg_button_hover": "#453359",
        "accent":          "#a855f7",
        "accent_dim":      "#7a3fb8",
        "accent_text":     "#ffffff",
        "ok":              "#2ecc71",
        "ok_hover":        "#27ae60",
        "danger":          "#e74c3c",
        "danger_hover":    "#c0392b",
        "warn":            "#f1c40f",
        "text":            "#e6dcf5",
        "text_dim":        "#a395b8",
        "text_muted":      "#6b5f7d",
        "border":          "#3d2f52",
        "border_focus":    "#a855f7",
        "tx_prefix":       "#2ecc71",
        "tx_text":         "#a395b8",
    }


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    """h in [0,1), s and l in [0,1]."""
    r, g, b = colorsys.hls_to_rgb(h % 1.0, l, s)
    return "#{:02x}{:02x}{:02x}".format(
        max(0, min(255, int(round(r * 255)))),
        max(0, min(255, int(round(g * 255)))),
        max(0, min(255, int(round(b * 255)))),
    )


def random_palette() -> dict[str, str]:
    """
    Generate a random but harmonious palette.

    Strategy:
        * pick a random hue for the "background family"
        * pick a random hue for the "accent family" (usually complementary
          or analogous to bg)
        * pick a random hue for the "danger family" (near red-ish, but jittered)
        * pick a random hue for the "ok family" (near green-ish, but jittered)
        * build all 20 keys with sensible lightness/saturation ranges
    """
    rng = random

    # --- background family ---
    bg_hue = rng.random()
    # light or dark theme, both allowed
    is_light = rng.random() < 0.25

    if is_light:
        bg_root_l = rng.uniform(0.90, 0.96)
        bg_panel_l = rng.uniform(0.95, 0.99)
        bg_input_l = rng.uniform(0.97, 1.00)
        bg_button_l = rng.uniform(0.85, 0.92)
        bg_button_hover_l = rng.uniform(0.78, 0.86)
        text_l = rng.uniform(0.08, 0.15)
        text_dim_l = rng.uniform(0.30, 0.42)
        text_muted_l = rng.uniform(0.50, 0.60)
        border_l = rng.uniform(0.75, 0.85)
        bg_s = rng.uniform(0.05, 0.20)
        text_s = rng.uniform(0.05, 0.25)
    else:
        bg_root_l = rng.uniform(0.05, 0.12)
        bg_panel_l = rng.uniform(0.08, 0.16)
        bg_input_l = rng.uniform(0.11, 0.20)
        bg_button_l = rng.uniform(0.15, 0.24)
        bg_button_hover_l = rng.uniform(0.20, 0.30)
        text_l = rng.uniform(0.85, 0.95)
        text_dim_l = rng.uniform(0.60, 0.72)
        text_muted_l = rng.uniform(0.40, 0.52)
        border_l = rng.uniform(0.20, 0.30)
        bg_s = rng.uniform(0.10, 0.40)
        text_s = rng.uniform(0.05, 0.25)

    # --- accent family ---
    # either complementary or analogous
    if rng.random() < 0.5:
        accent_hue = (bg_hue + 0.5) % 1.0
    else:
        accent_hue = (bg_hue + rng.uniform(-0.15, 0.15)) % 1.0

    accent_s = rng.uniform(0.65, 0.95)
    accent_l = rng.uniform(0.50, 0.68)
    accent_dim_l = max(0.20, accent_l - rng.uniform(0.15, 0.25))

    # accent_text: black or white depending on accent lightness
    accent_text = "#000000" if accent_l > 0.62 else "#ffffff"

    # --- semantic colors ---
    ok_hue = (0.33 + rng.uniform(-0.06, 0.06)) % 1.0
    ok_s = rng.uniform(0.60, 0.85)
    ok_l = rng.uniform(0.48, 0.62)
    ok_hover_l = max(0.20, ok_l - 0.10)

    danger_hue = (0.00 + rng.uniform(-0.05, 0.05)) % 1.0
    danger_s = rng.uniform(0.65, 0.90)
    danger_l = rng.uniform(0.45, 0.58)
    danger_hover_l = max(0.20, danger_l - 0.10)

    warn_hue = (0.13 + rng.uniform(-0.04, 0.04)) % 1.0
    warn_s = rng.uniform(0.75, 0.95)
    warn_l = rng.uniform(0.55, 0.68)

    def bg(h, s, l):
        return _hsl_to_hex(h, s, l)

    palette = {
        "bg_root":         bg(bg_hue, bg_s * 0.9, bg_root_l),
        "bg_panel":        bg(bg_hue, bg_s, bg_panel_l),
        "bg_input":        bg(bg_hue, bg_s, bg_input_l),
        "bg_button":       bg(bg_hue, bg_s, bg_button_l),
        "bg_button_hover": bg(bg_hue, bg_s, bg_button_hover_l),

        "accent":          bg(accent_hue, accent_s, accent_l),
        "accent_dim":      bg(accent_hue, accent_s * 0.9, accent_dim_l),
        "accent_text":     accent_text,

        "ok":              bg(ok_hue, ok_s, ok_l),
        "ok_hover":        bg(ok_hue, ok_s, ok_hover_l),
        "danger":          bg(danger_hue, danger_s, danger_l),
        "danger_hover":    bg(danger_hue, danger_s, danger_hover_l),
        "warn":            bg(warn_hue, warn_s, warn_l),

        "text":            bg(bg_hue, text_s, text_l),
        "text_dim":        bg(bg_hue, text_s, text_dim_l),
        "text_muted":      bg(bg_hue, text_s, text_muted_l),

        "border":          bg(bg_hue, bg_s, border_l),
        "border_focus":    bg(accent_hue, accent_s, accent_l),

        "tx_prefix":       bg(ok_hue, ok_s, ok_l),
        "tx_text":         bg(bg_hue, text_s, text_dim_l),
    }
    return palette


def randomize_custom_palette() -> dict[str, str]:
    """Generate a random palette, save it as custom, return it."""
    p = random_palette()
    save_custom_palette(p)
    return p


def has_custom_palette() -> bool:
    s = QSettings()
    s.beginGroup("custom_theme")
    exists = s.contains("bg_root")
    s.endGroup()
    return exists


def load_custom_palette() -> dict[str, str] | None:
    if not has_custom_palette():
        return None
    s = QSettings()
    s.beginGroup("custom_theme")
    palette = {k: s.value(k, "", type=str) for k in _KEYS}
    s.endGroup()
    for k in _KEYS:
        if not palette[k]:
            return None
    return palette


def save_custom_palette(palette: dict[str, str]) -> None:
    s = QSettings()
    s.beginGroup("custom_theme")
    for k in _KEYS:
        if k in palette:
            s.setValue(k, palette[k])
    s.endGroup()
    s.sync()


def reset_custom_palette() -> None:
    s = QSettings()
    s.beginGroup("custom_theme")
    s.remove("")
    s.endGroup()
    s.sync()