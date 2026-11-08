"""Central light/dark design tokens shared by Streamlit styling and components."""

from __future__ import annotations


LIGHT_TOKENS = {
    "text": "#17312b",
    "muted": "#61756f",
    "surface": "#ffffff",
    "surface_raised": "#f8fbf9",
    "sidebar": "#eaf1ee",
    "border": "#dce7e2",
    "accent": "#087f63",
    "background": "#f3f7f5",
    "bull": "#08734f",
    "bear": "#b42335",
    "caution": "#8a5b00",
    "info": "#245b83",
}

DARK_TOKENS = {
    "text": "#edf4f2",
    "muted": "#91a6a3",
    "surface": "#111d20",
    "surface_raised": "#172427",
    "sidebar": "#0e191c",
    "border": "#26383a",
    "accent": "#76e0b2",
    "background": "#0b1417",
    "bull": "#8ee6b6",
    "bear": "#ff9999",
    "caution": "#ffd27d",
    "info": "#91c7f4",
}

SPACING_PX = (4, 8, 12, 16, 24, 32, 40, 48)
FONT_STACKS = {
    "body": "Manrope, system-ui, 'Segoe UI', Arial, sans-serif",
    "financial": "'DM Mono', ui-monospace, 'Cascadia Mono', monospace",
}


def get_theme_tokens(theme: object) -> dict[str, str]:
    """Return a fresh token mapping for the selected Streamlit theme."""
    return dict(LIGHT_TOKENS if str(theme).casefold() == "light" else DARK_TOKENS)


def css_variable_declarations(tokens: dict[str, str]) -> str:
    """Serialize semantic tokens into CSS custom-property declarations."""
    names = {
        "text": "text-color",
        "muted": "market-lens-muted",
        "surface": "secondary-background-color",
        "surface_raised": "market-lens-surface-raised",
        "sidebar": "market-lens-sidebar",
        "border": "border-color",
        "accent": "primary-color",
        "background": "background-color",
        "bull": "market-lens-bull",
        "bear": "market-lens-bear",
        "caution": "market-lens-caution",
        "info": "market-lens-info",
    }
    declarations = [f"--{names[key]}:{tokens[key]}" for key in names]
    declarations.extend((
        f"--market-lens-font-body:{FONT_STACKS['body']}",
        f"--market-lens-font-financial:{FONT_STACKS['financial']}",
    ))
    declarations.extend(
        f"--ml-space-{index}:{value}px" for index, value in enumerate(SPACING_PX, start=1)
    )
    return ";".join(declarations)
