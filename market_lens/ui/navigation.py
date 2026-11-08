"""Stable workspace state and data-scope helpers for the single-page app."""

from collections.abc import MutableMapping


WORKSPACES = (
    "Market Overview",
    "Discovery",
    "Company Research",
    "Watchlist",
)
WORKSPACE_KEY = "market_lens_workspace"
DEFAULT_WORKSPACE = "Market Overview"
SAVED_WIDGET_STATE_KEY = "market_lens_saved_workspace_widget_state"
RESTORE_PENDING_KEY = "market_lens_restore_workspace_widget_state"

WORKSPACE_WIDGET_KEYS = {
    "Market Overview": (
        "market_chart_interval", "market_chart_range", "market_chart_style",
        "market_chart_averages",
    ),
    "Discovery": (
        "discovery_index_tabs", "discovery_event_window", "industry_directory_search",
        "industry_directory_selection",
    ),
    "Company Research": (
        "research_desk_tabs", "headline_sentiment_filter",
    ),
    "Watchlist": ("industry_filter",),
}


def normalize_workspace(value: object) -> str:
    """Return a supported workspace while keeping Overview as the safe default."""
    candidate = str(value or "").strip()
    return candidate if candidate in WORKSPACES else DEFAULT_WORKSPACE


def initialize_workspace_state(state: MutableMapping) -> str:
    """Initialize/repair the persistent workspace session-state value."""
    workspace = normalize_workspace(state.get(WORKSPACE_KEY))
    state[WORKSPACE_KEY] = workspace
    return workspace


def workspace_requires_ticker_data(workspace: object) -> bool:
    """Whether the active workspace consumes the selected-ticker core payload.

    Discovery owns its own directory/calendar loaders and must not trigger the
    selected ticker's quote, options, or profile requests just by opening it.
    """
    return normalize_workspace(workspace) != "Discovery"


def save_workspace_widget_state(state: MutableMapping) -> None:
    """Snapshot view-specific control state before Streamlit prunes hidden widgets."""
    saved = dict(state.get(SAVED_WIDGET_STATE_KEY, {}))
    for keys in WORKSPACE_WIDGET_KEYS.values():
        for key in keys:
            if key in state:
                saved[key] = state[key]
    state[SAVED_WIDGET_STATE_KEY] = saved
    state[RESTORE_PENDING_KEY] = True


def restore_workspace_widget_state(state: MutableMapping, workspace: object) -> None:
    """Restore controls for a workspace after navigation hid those widgets."""
    if not state.get(RESTORE_PENDING_KEY):
        return
    saved = state.get(SAVED_WIDGET_STATE_KEY, {})
    for key in WORKSPACE_WIDGET_KEYS[normalize_workspace(workspace)]:
        if key in saved:
            state[key] = saved[key]
    state[RESTORE_PENDING_KEY] = False
