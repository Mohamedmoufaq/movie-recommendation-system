"""Shared look & feel + small wrappers that work on old AND new Streamlit versions."""
from __future__ import annotations

import html

import pandas as pd
import streamlit as st

# Colours match .streamlit/config.toml (dark theme, red accent)
PALETTE = ["#E50914", "#F5B301", "#2EC4B6", "#7B8CDE", "#FF7A59", "#9BD770", "#C77DFF", "#4CC9F0"]
RED_SCALE = ["#2A1215", "#E50914"]

CSS = """
<style>
.block-container {padding-top: 2rem; padding-bottom: 3rem;}
.kpi {background:#161B22; border:1px solid #262C36; border-radius:10px; padding:14px 16px; height:100%;}
.kpi .label {color:#9AA4B2; font-size:0.82rem; margin-bottom:2px;}
.kpi .value {color:#FAFAFA; font-size:1.65rem; font-weight:700; line-height:1.25;}
.kpi .sub {color:#7D8795; font-size:0.74rem; margin-top:2px;}
.chip {display:inline-block; background:#262C36; border-radius:999px; padding:2px 11px;
       margin:0 6px 6px 0; font-size:0.78rem; color:#E6E8EB;}
.movie-title {font-size:2rem; font-weight:700; margin:0 0 4px 0; line-height:1.2;}
.muted {color:#9AA4B2; font-size:0.9rem;}
.why {color:#9AA4B2; font-size:0.76rem; line-height:1.3;}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def esc(text) -> str:
    return html.escape(str(text))


def md_escape(text) -> str:
    """Stop '$' or '*' in titles from being treated as markdown/LaTeX."""
    return str(text).replace("$", r"\$").replace("*", r"\*").replace("_", r"\_")


def chips(items) -> str:
    return "".join(f'<span class="chip">{esc(i)}</span>' for i in items)


def kpi_cards(items: list[tuple]) -> None:
    """items = [(label, value, small_text), ...]"""
    for col, (label, value, sub) in zip(st.columns(len(items)), items):
        col.markdown(f'<div class="kpi"><div class="label">{esc(label)}</div>'
                     f'<div class="value">{esc(value)}</div><div class="sub">{esc(sub)}</div></div>',
                     unsafe_allow_html=True)


# ---------- number formatting ----------
def fmt_int(x) -> str:
    return "—" if pd.isna(x) else f"{int(round(x)):,}"


def fmt_money(x) -> str:
    if pd.isna(x):
        return "—"
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(x) >= limit:
            return f"${x / limit:,.1f}{suffix}"
    return f"${x:,.0f}"


# ---------- Streamlit-version-safe wrappers ----------
def show_chart(fig) -> None:
    try:
        st.plotly_chart(fig, width="stretch")
    except Exception:
        st.plotly_chart(fig, use_container_width=True)


def show_df(df, **kwargs) -> None:
    try:
        st.dataframe(df, width="stretch", hide_index=True, **kwargs)
    except Exception:
        st.dataframe(df, use_container_width=True, hide_index=True, **kwargs)


def show_image(img) -> None:
    try:
        st.image(img, width="stretch")
    except Exception:
        st.image(img, use_container_width=True)


def style_fig(fig, height: int = 380, legend: bool = False):
    """One consistent chart style for the whole dashboard."""
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        colorway=PALETTE, height=height, margin=dict(l=8, r=8, t=56, b=8),
        title=dict(font=dict(size=16)), showlegend=legend,
        font=dict(size=13), hoverlabel=dict(font_size=13),
    )
    fig.update_xaxes(gridcolor="#222833", zerolinecolor="#222833")
    fig.update_yaxes(gridcolor="#222833", zerolinecolor="#222833")
    return fig
