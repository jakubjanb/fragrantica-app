from __future__ import annotations

from pathlib import Path
from typing import Any

import plotly.graph_objects as go
import streamlit.components.v1 as components

_COMPONENT_DIR = Path(__file__).resolve().parent.parent / "components" / "sunburst_click"
_sunburst_click_component = components.declare_component(
    "sunburst_click",
    path=str(_COMPONENT_DIR),
)


def render_sunburst_click(
    fig: go.Figure,
    *,
    key: str,
    height: int = 760,
    config: dict[str, Any] | None = None,
    default: Any = None,
) -> Any:
    merged_config = {
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        "responsive": True,
    }
    if config:
        merged_config.update(config)

    return _sunburst_click_component(
        figure=fig.to_plotly_json(),
        config=merged_config,
        height=height,
        key=key,
        default=default,
    )
