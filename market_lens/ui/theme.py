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


def resolve_active_theme(session_theme: object, streamlit_theme: object) -> str:
    """Use an explicit synchronized mode or Streamlit's resolved light/dark mode."""
    session_mode = str(session_theme or "").casefold()
    streamlit_mode = str(streamlit_theme or "").casefold()
    if session_mode in {"light", "dark"}:
        return session_mode
    if streamlit_mode in {"light", "dark"}:
        return streamlit_mode
    return "dark"


def css_variable_declarations(tokens: dict[str, str]) -> str:
    """Serialize semantic tokens into CSS custom-property declarations."""
    names = {
        "text": "market-lens-text",
        "muted": "market-lens-muted",
        "surface": "market-lens-surface",
        "surface_raised": "market-lens-surface-raised",
        "sidebar": "market-lens-sidebar",
        "border": "market-lens-border",
        "accent": "market-lens-accent",
        "background": "market-lens-background",
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



def app_background_css() -> str:
    """Theme the app shell and nested view with one token-driven gradient."""
    return """
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
      background-color:var(--market-lens-background) !important;
      background-image:radial-gradient(
        ellipse at 78% -5%,
        color-mix(in srgb,var(--market-lens-accent) 11%,var(--market-lens-background)) 0%,
        var(--market-lens-background) 48%
      ) !important;
      color:var(--market-lens-text) !important;
    }
    """
