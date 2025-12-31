from __future__ import annotations

import pandas as pd
import plotly.express as px


def make_figure(df: pd.DataFrame, brand: str):
    """Create a Plotly scatter figure for a given brand.

    X: rating, Y: votes (log scale). Point size proportional to votes.
    """
    if df.empty or "brand" not in df.columns:
        return px.scatter(title="No data")

    sub = df[df["brand"] == brand].copy()
    if sub.empty:
        return px.scatter(title=f"{brand} — Rating vs Votes")

    # Safeguard ranges
    x_min = float(sub["rating"].min()) if not sub["rating"].isna().all() else 0.0
    x_max = float(sub["rating"].max()) if not sub["rating"].isna().all() else 5.0

    # Ensure url column exists for interactivity (click to open)
    if "url" not in sub.columns:
        sub["url"] = ""

    # Clip votes to at least 1 for plotting on log scale while keeping original values
    sub["votes_plot"] = sub["votes"].clip(lower=1)

    fig = px.scatter(
        sub,
        x="rating",
        y="votes_plot",
        hover_name="name",
        size="votes",
        size_max=48,
        color="rating",
        color_continuous_scale="Viridis",
        labels={"rating": "Rating", "votes_plot": "Votes"},
        title=f"{brand} — Rating vs Votes",
        # Pass URL and original votes to front-end for click handling and hover
        custom_data=["url", "votes"],
    )

    fig.update_traces(
        hovertemplate="<b>%{hovertext}</b><br>Rating: %{x:.2f}<br>Votes: %{customdata[1]:,}<extra></extra>",
        marker=dict(line=dict(width=0.5, color="rgba(0,0,0,0.2)")),
    )

    fig.update_layout(
        template="plotly_white",
        plot_bgcolor="white",
        paper_bgcolor="white",
        title=dict(x=0.5, xanchor="center", font=dict(size=24, family="Arial, sans-serif")),
        # Taller chart and tighter top margin to maximize plotting area
        height=900,
        margin=dict(l=80, r=80, t=70, b=80),
        hovermode="closest",
        # Fire click events without entering selection mode (prevents dimming of other points)
        clickmode="event",
        coloraxis_colorbar=dict(title="Rating", ticks="outside"),
        xaxis=dict(
            title="Rating",
            range=[x_min - 0.1, x_max + 0.1],
            zeroline=False,
            showgrid=True,
            gridcolor="rgba(200,200,200,0.2)",
            tickformat=".2f",
        ),
        yaxis=dict(
            title="Votes (log scale)",
            type="log",
            showgrid=True,
            gridcolor="rgba(200,200,200,0.2)",
        ),
        # Make plot responsive
        autosize=True,
    )

    # High-rating band
    try:
        fig.add_vrect(
            x0=4.0,
            x1=x_max + 0.2,
            fillcolor="LightGreen",
            opacity=0.08,
            line_width=0,
            annotation_text="High rating (>=4.0)",
            annotation_position="top left",
        )
    except Exception:
        # Some backends may not support add_vrect; ignore gracefully
        pass

    return fig
