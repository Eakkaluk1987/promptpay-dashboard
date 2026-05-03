"""
dashboard.py — Streamlit multi-page dashboard for the PromptPay Monitoring Dashboard.

Polls the FastAPI backend (port 8000) for CSV-backed metrics and renders them
across six pages: Overview, Hourly Volume, 7-Day Trend, Response Code Summary,
Proxy Type, and Hourly by Proxy.
"""

from __future__ import annotations

import os
import requests
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Design tokens — dark banking theme
# ---------------------------------------------------------------------------

# Background layers
BG_PAGE    = "#0d1117"   # deepest background (page)
BG_CARD    = "#161b22"   # card / panel surface
BG_SURFACE = "#1c2333"   # slightly lighter surface (chart bg, table rows)
BG_BORDER  = "#30363d"   # subtle border / divider

# Brand / accent
ACCENT_BLUE   = "#58a6ff"   # primary interactive / highlight
ACCENT_TEAL   = "#39d0d8"   # secondary accent

# Semantic colours
COLOR_SUCCESS = "#3fb950"   # green  — success rate, positive delta
COLOR_DANGER  = "#f85149"   # red    — fail count, negative delta
COLOR_WARNING = "#d29922"   # amber  — warning states
COLOR_NEUTRAL = "#8b949e"   # muted text / labels

# Chart palette (6 distinct colours, accessible on dark bg)
CHART_PALETTE = [
    "#58a6ff",  # blue
    "#3fb950",  # green
    "#f78166",  # coral
    "#d2a8ff",  # lavender
    "#ffa657",  # orange
    "#39d0d8",  # teal
]

# Plotly layout defaults shared across all charts
_PLOTLY_BASE = dict(
    paper_bgcolor=BG_CARD,
    plot_bgcolor=BG_SURFACE,
    font=dict(family="Inter, Segoe UI, sans-serif", color="#c9d1d9", size=13),
    title_font=dict(size=16, color="#e6edf3"),
    legend=dict(
        bgcolor=BG_CARD,
        bordercolor=BG_BORDER,
        borderwidth=1,
        font=dict(color="#c9d1d9"),
    ),
    xaxis=dict(
        gridcolor=BG_BORDER,
        linecolor=BG_BORDER,
        tickcolor=BG_BORDER,
        tickfont=dict(color=COLOR_NEUTRAL),
        title_font=dict(color=COLOR_NEUTRAL),
        zeroline=False,
    ),
    yaxis=dict(
        gridcolor=BG_BORDER,
        linecolor=BG_BORDER,
        tickcolor=BG_BORDER,
        tickfont=dict(color=COLOR_NEUTRAL),
        title_font=dict(color=COLOR_NEUTRAL),
        zeroline=False,
    ),
    margin=dict(l=60, r=30, t=60, b=60),
    hoverlabel=dict(
        bgcolor=BG_SURFACE,
        bordercolor=BG_BORDER,
        font=dict(color="#e6edf3"),
    ),
)

# ---------------------------------------------------------------------------
# Global CSS injection
# ---------------------------------------------------------------------------

_CSS = f"""
<style>
/* ── Page background ── */
.stApp {{
    background-color: {BG_PAGE};
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background-color: {BG_CARD};
    border-right: 1px solid {BG_BORDER};
}}
[data-testid="stSidebar"] .stRadio label {{
    color: #c9d1d9 !important;
    font-size: 0.9rem;
}}
[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {{
    color: {COLOR_NEUTRAL};
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.25rem;
}}

/* ── Page title / headers ── */
h1, h2, h3 {{
    color: #e6edf3 !important;
    font-family: "Inter", "Segoe UI", sans-serif !important;
}}
h1 {{ font-size: 1.6rem !important; font-weight: 700 !important; }}
h2 {{ font-size: 1.2rem !important; font-weight: 600 !important; }}

/* ── KPI card ── */
.kpi-card {{
    background: {BG_CARD};
    border: 1px solid {BG_BORDER};
    border-radius: 10px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.5rem;
    position: relative;
    overflow: hidden;
}}
.kpi-card::before {{
    content: "";
    position: absolute;
    top: 0; left: 0;
    width: 4px; height: 100%;
    border-radius: 10px 0 0 10px;
}}
.kpi-card.blue::before   {{ background: {ACCENT_BLUE}; }}
.kpi-card.green::before  {{ background: {COLOR_SUCCESS}; }}
.kpi-card.red::before    {{ background: {COLOR_DANGER}; }}
.kpi-card.teal::before   {{ background: {ACCENT_TEAL}; }}

.kpi-label {{
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: {COLOR_NEUTRAL};
    margin-bottom: 0.35rem;
}}
.kpi-value {{
    font-size: 1.9rem;
    font-weight: 700;
    color: #e6edf3;
    line-height: 1.1;
}}
.kpi-sub {{
    font-size: 0.78rem;
    color: {COLOR_NEUTRAL};
    margin-top: 0.3rem;
}}
.kpi-badge {{
    display: inline-block;
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    margin-top: 0.4rem;
}}
.badge-green {{ background: rgba(63,185,80,0.15); color: {COLOR_SUCCESS}; }}
.badge-red   {{ background: rgba(248,81,73,0.15);  color: {COLOR_DANGER}; }}
.badge-blue  {{ background: rgba(88,166,255,0.15); color: {ACCENT_BLUE}; }}

/* ── Section divider ── */
.section-header {{
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: {COLOR_NEUTRAL};
    border-bottom: 1px solid {BG_BORDER};
    padding-bottom: 0.4rem;
    margin: 1.4rem 0 1rem 0;
}}

/* ── Dataframe / table ── */
[data-testid="stDataFrame"] {{
    border: 1px solid {BG_BORDER} !important;
    border-radius: 8px !important;
    overflow: hidden;
}}

/* ── Metric widget (fallback) ── */
[data-testid="stMetric"] {{
    background: {BG_CARD};
    border: 1px solid {BG_BORDER};
    border-radius: 8px;
    padding: 0.8rem 1rem;
}}
[data-testid="stMetricLabel"] {{ color: {COLOR_NEUTRAL} !important; }}
[data-testid="stMetricValue"] {{ color: #e6edf3 !important; }}

/* ── Error / info banners ── */
[data-testid="stAlert"] {{
    border-radius: 8px !important;
}}
</style>
"""


def _inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data fetching helper
# ---------------------------------------------------------------------------


@st.cache_data(ttl=60)
def _fetch_cached(endpoint: str) -> dict | list | None:
    """Cached HTTP call — returns parsed JSON or None on any failure.
    Side-effect-free: callers are responsible for showing error messages.
    """
    try:
        response = requests.get(BASE_URL + endpoint, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None


def fetch(endpoint: str) -> dict | list | None:
    """Fetch JSON from the backend, showing an st.error() banner on failure."""
    try:
        response = requests.get(BASE_URL + endpoint, timeout=10)
        if response.status_code != 200:
            st.error(
                f"Backend returned HTTP {response.status_code} for {endpoint}. "
                "Is FastAPI running on port 8000?"
            )
            return None
        return response.json()
    except ConnectionError:
        st.error("Backend unavailable — is FastAPI running on port 8000?")
        return None
    except Exception:
        st.error("Backend unavailable — is FastAPI running on port 8000?")
        return None


# ---------------------------------------------------------------------------
# KPI card helper
# ---------------------------------------------------------------------------

def _kpi_card(
    label: str,
    value: str,
    sub: str = "",
    badge: str = "",
    badge_style: str = "blue",
    accent: str = "blue",
) -> None:
    """Render a styled KPI card using HTML."""
    badge_html = (
        f'<div class="kpi-badge badge-{badge_style}">{badge}</div>'
        if badge else ""
    )
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    st.markdown(
        f"""
        <div class="kpi-card {accent}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {sub_html}
            {badge_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Plotly layout helper
# ---------------------------------------------------------------------------

def _apply_dark_layout(fig: go.Figure, title: str = "", **kwargs) -> go.Figure:
    """Apply the shared dark theme layout to a Plotly figure."""
    layout = dict(**_PLOTLY_BASE)
    if title:
        layout["title"] = dict(text=title, font=dict(size=16, color="#e6edf3"), x=0.01)
    layout.update(kwargs)
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Page renderers
# ---------------------------------------------------------------------------


def render_overview() -> None:
    """Overview page: KPI cards + success/fail gauge from /api/overview."""
    st.markdown('<div class="section-header">Key Performance Indicators</div>', unsafe_allow_html=True)

    try:
        data = fetch("/api/overview")
    except Exception:
        st.error("Backend unavailable — is FastAPI running on port 8000?")
        return

    if data is None:
        return

    total_txn       = data.get("total_txn", 0)
    success_rate    = data.get("success_rate", 0.0)
    fail_count      = data.get("fail_count", 0)
    total_amount    = data.get("total_amount_thb", 0.0)
    success_count   = total_txn - fail_count

    # ── KPI row ──────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _kpi_card(
            label="Total Transactions",
            value=f"{total_txn:,}",
            sub="All transaction types",
            badge="LIVE",
            badge_style="blue",
            accent="blue",
        )
    with c2:
        rate_pct = success_rate * 100
        _kpi_card(
            label="Success Rate",
            value=f"{rate_pct:.2f}%",
            sub=f"{success_count:,} successful",
            badge="✓ HEALTHY" if rate_pct >= 98 else "⚠ DEGRADED",
            badge_style="green" if rate_pct >= 98 else "red",
            accent="green",
        )
    with c3:
        _kpi_card(
            label="Failed Transactions",
            value=f"{fail_count:,}",
            sub=f"{(1 - success_rate) * 100:.2f}% of total",
            badge=f"{(1 - success_rate) * 100:.2f}% FAIL RATE",
            badge_style="red",
            accent="red",
        )
    with c4:
        billions = total_amount / 1_000_000_000
        _kpi_card(
            label="Total Volume (THB)",
            value=f"฿{billions:.2f}B",
            sub=f"{total_amount:,.0f} THB",
            badge="THB",
            badge_style="blue",
            accent="teal",
        )

    st.markdown('<div class="section-header">Success vs Failure Breakdown</div>', unsafe_allow_html=True)

    # ── Gauge + donut row ─────────────────────────────────────────────────
    g1, g2 = st.columns([1, 1])

    with g1:
        # Gauge chart for success rate
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=success_rate * 100,
            number=dict(suffix="%", font=dict(size=36, color="#e6edf3")),
            delta=dict(reference=99.0, valueformat=".2f", suffix="%",
                       increasing=dict(color=COLOR_SUCCESS),
                       decreasing=dict(color=COLOR_DANGER)),
            gauge=dict(
                axis=dict(range=[90, 100], tickcolor=COLOR_NEUTRAL,
                          tickfont=dict(color=COLOR_NEUTRAL)),
                bar=dict(color=COLOR_SUCCESS if success_rate >= 0.98 else COLOR_WARNING),
                bgcolor=BG_SURFACE,
                bordercolor=BG_BORDER,
                steps=[
                    dict(range=[90, 95], color="rgba(248,81,73,0.15)"),
                    dict(range=[95, 98], color="rgba(210,153,34,0.15)"),
                    dict(range=[98, 100], color="rgba(63,185,80,0.15)"),
                ],
                threshold=dict(
                    line=dict(color=COLOR_SUCCESS, width=2),
                    thickness=0.75,
                    value=99,
                ),
            ),
            title=dict(text="Success Rate", font=dict(color=COLOR_NEUTRAL, size=13)),
        ))
        _apply_dark_layout(fig_gauge, height=280, margin=dict(l=30, r=30, t=40, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)

    with g2:
        # Donut chart: success vs fail
        fig_donut = go.Figure(go.Pie(
            labels=["Success", "Failed"],
            values=[success_count, fail_count],
            hole=0.65,
            marker=dict(
                colors=[COLOR_SUCCESS, COLOR_DANGER],
                line=dict(color=BG_CARD, width=3),
            ),
            textinfo="label+percent",
            textfont=dict(color="#e6edf3", size=12),
            hovertemplate="<b>%{label}</b><br>Count: %{value:,}<br>Share: %{percent}<extra></extra>",
        ))
        fig_donut.add_annotation(
            text=f"{success_rate * 100:.1f}%<br><span style='font-size:11px;color:{COLOR_NEUTRAL}'>Success</span>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=22, color="#e6edf3"),
            align="center",
        )
        _apply_dark_layout(
            fig_donut,
            title="Transaction Outcome",
            showlegend=True,
            height=280,
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig_donut, use_container_width=True)


def render_hourly_volume() -> None:
    """Hourly Volume page: styled line chart per tx_type."""
    st.markdown('<div class="section-header">Hourly Transaction Volume by Type</div>', unsafe_allow_html=True)

    try:
        data = fetch("/api/hourly-volume")
    except Exception:
        st.error("Backend unavailable — is FastAPI running on port 8000?")
        return

    if data is None:
        return
    if not data:
        st.info("No hourly volume data available.")
        return

    df = pd.DataFrame(data)
    tx_types = sorted(df["tx_type"].unique()) if "tx_type" in df.columns else []

    fig = go.Figure()
    for i, tx_type in enumerate(tx_types):
        subset = df[df["tx_type"] == tx_type].sort_values("hour")
        color = CHART_PALETTE[i % len(CHART_PALETTE)]
        fig.add_trace(go.Scatter(
            x=subset["hour"],
            y=subset["total"],
            mode="lines+markers",
            name=tx_type,
            line=dict(color=color, width=2.5),
            marker=dict(color=color, size=6, line=dict(color=BG_CARD, width=1.5)),
            hovertemplate=f"<b>{tx_type}</b><br>Hour: %{{x}}:00<br>Total: %{{y:,}}<extra></extra>",
            fill="tozeroy",
            fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.06)",
        ))

    _apply_dark_layout(
        fig,
        title="Hourly Transaction Volume",
        xaxis=dict(
            **_PLOTLY_BASE["xaxis"],
            title="Hour of Day",
            tickmode="linear",
            tick0=0, dtick=2,
            tickformat="%H:00",
        ),
        yaxis=dict(**_PLOTLY_BASE["yaxis"], title="Transaction Count"),
        height=420,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary table below chart
    if "tx_type" in df.columns and "total" in df.columns:
        st.markdown('<div class="section-header">Peak Hours by Transaction Type</div>', unsafe_allow_html=True)
        summary = (
            df.groupby("tx_type")
            .agg(total_volume=("total", "sum"), peak_hour=("total", "idxmax"))
            .reset_index()
        )
        # Map idxmax index back to hour value
        summary["peak_hour"] = summary["peak_hour"].apply(
            lambda idx: f"{int(df.loc[idx, 'hour']):02d}:00" if idx in df.index else "—"
        )
        summary.columns = ["Transaction Type", "Total Volume", "Peak Hour"]
        try:
            st.dataframe(
                summary.style.format({"Total Volume": "{:,}"}),
                use_container_width=True,
                hide_index=True,
            )
        except Exception:
            st.dataframe(summary, use_container_width=True, hide_index=True)


def render_trend() -> None:
    """7-Day Trend page: area chart aggregated by date."""
    st.markdown('<div class="section-header">7-Day Transaction Volume Trend</div>', unsafe_allow_html=True)

    try:
        data = fetch("/api/trend")
    except Exception:
        st.error("Backend unavailable — is FastAPI running on port 8000?")
        return

    if data is None:
        return
    if not data:
        st.info("No trend data available.")
        return

    df = pd.DataFrame(data)

    if "date" not in df.columns or "count" not in df.columns:
        st.warning("Unexpected data format from /api/trend.")
        return

    daily = df.groupby("date", as_index=False)["count"].sum().sort_values("date")

    # Compute day-over-day delta for annotation
    daily["delta"] = daily["count"].diff()
    daily["delta_pct"] = daily["count"].pct_change() * 100

    fig = go.Figure()

    # Shaded area
    fig.add_trace(go.Scatter(
        x=daily["date"],
        y=daily["count"],
        mode="lines+markers",
        name="Daily Volume",
        line=dict(color=ACCENT_BLUE, width=3),
        marker=dict(color=ACCENT_BLUE, size=8, line=dict(color=BG_CARD, width=2)),
        fill="tozeroy",
        fillcolor="rgba(88,166,255,0.10)",
        hovertemplate="<b>%{x}</b><br>Volume: %{y:,}<extra></extra>",
    ))

    # 7-day average reference line
    avg = daily["count"].mean()
    fig.add_hline(
        y=avg,
        line=dict(color=COLOR_WARNING, width=1.5, dash="dot"),
        annotation_text=f"7-day avg: {avg:,.0f}",
        annotation_font=dict(color=COLOR_WARNING, size=11),
        annotation_position="top right",
    )

    _apply_dark_layout(
        fig,
        title="Daily Transaction Volume (Last 7 Days)",
        xaxis=dict(**_PLOTLY_BASE["xaxis"], title="Date"),
        yaxis=dict(**_PLOTLY_BASE["yaxis"], title="Transaction Count"),
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Delta summary cards
    st.markdown('<div class="section-header">Day-over-Day Change</div>', unsafe_allow_html=True)
    cols = st.columns(min(len(daily), 7))
    for i, (_, row) in enumerate(daily.iterrows()):
        with cols[i % len(cols)]:
            delta = row["delta"]
            delta_pct = row["delta_pct"]
            if pd.isna(delta):
                badge, badge_style = "BASE", "blue"
            elif delta >= 0:
                badge, badge_style = f"▲ {delta_pct:.1f}%", "green"
            else:
                badge, badge_style = f"▼ {abs(delta_pct):.1f}%", "red"
            _kpi_card(
                label=str(row["date"]),
                value=f"{int(row['count']):,}",
                badge=badge,
                badge_style=badge_style,
                accent="blue",
            )


def render_response_codes() -> None:
    """Response Code Summary page: styled table + bar chart."""
    st.markdown('<div class="section-header">Response Code Distribution</div>', unsafe_allow_html=True)

    try:
        data = fetch("/api/response-codes")
    except Exception:
        st.error("Backend unavailable — is FastAPI running on port 8000?")
        return

    if data is None:
        return
    if not data:
        st.info("No response code data available.")
        return

    df = pd.DataFrame(data)
    columns = [c for c in ["tsc_code", "origin_iap", "dest_iap", "count"] if c in df.columns]
    df = df[columns].copy()

    if "count" in df.columns:
        df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0).astype(int)
        df["tsc_code"] = df["tsc_code"].astype(str)

    # Aggregate by tsc_code — multiple rows can share the same code (different IAP pairs)
    # For the chart: sum count per code; for the table: keep all rows
    df_chart = (
        df.groupby("tsc_code", as_index=False)["count"]
        .sum()
        .sort_values("count", ascending=False)
    )
    total = df_chart["count"].sum()
    df_chart["share_%"] = (df_chart["count"] / total * 100).round(2) if total > 0 else 0.0

    # Full detail table (all rows, sorted by count)
    df_table = df.sort_values("count", ascending=False).copy()
    df_table["share_%"] = (df_table["count"] / total * 100).round(2) if total > 0 else 0.0

    # Top-N bar chart (aggregated by tsc_code)
    top = df_chart.head(15).copy()
    if "tsc_code" in top.columns and "count" in top.columns:
        n = len(top)
        bar_colors = [
            f"rgba(88,166,255,{0.45 + 0.55 * (n - i) / n:.2f})"
            for i in range(n)
        ]
        fig = go.Figure(go.Bar(
            x=top["count"],
            y=top["tsc_code"],
            orientation="h",
            marker=dict(
                color=bar_colors,
                line=dict(color=BG_BORDER, width=0.5),
            ),
            hovertemplate="<b>Code %{y}</b><br>Total Count: %{x:,}<extra></extra>",
            text=top["count"].apply(lambda v: f"{v:,}"),
            textposition="outside",
            textfont=dict(color=COLOR_NEUTRAL, size=11),
        ))
        _apply_dark_layout(
            fig,
            title="Top Response Codes by Volume (aggregated)",
            xaxis=dict(**_PLOTLY_BASE["xaxis"], title="Transaction Count"),
            yaxis=dict(**_PLOTLY_BASE["yaxis"], title="TSC Code",
                       type="category", autorange="reversed"),
            height=max(300, len(top) * 32 + 80),
            margin=dict(l=80, r=80, t=60, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Full Response Code Table (all IAP pairs)</div>', unsafe_allow_html=True)
    # Cast StringDtype columns to object so pandas Styler works correctly
    for col in df_table.select_dtypes(include="string").columns:
        df_table[col] = df_table[col].astype(object)
    try:
        st.dataframe(
            df_table.style.format({"count": "{:,}", "share_%": "{:.2f}%"}),
            use_container_width=True,
            hide_index=True,
        )
    except Exception:
        st.dataframe(df_table, use_container_width=True, hide_index=True)


def render_proxy_type() -> None:
    """Proxy Type page: donut chart + KPI cards."""
    st.markdown('<div class="section-header">Proxy Type Distribution</div>', unsafe_allow_html=True)

    try:
        data = fetch("/api/proxy-type")
    except Exception:
        st.error("Backend unavailable — is FastAPI running on port 8000?")
        return

    if data is None:
        return
    if not data:
        st.info("No proxy type data available.")
        return

    df = pd.DataFrame(data)

    # ── KPI cards per proxy type ──────────────────────────────────────────
    cols = st.columns(len(df))
    accent_cycle = ["blue", "teal", "green"]
    for i, (_, row) in enumerate(df.iterrows()):
        with cols[i]:
            pct = float(row.get("percentage", 0))
            _kpi_card(
                label=str(row["proxy_type"]),
                value=f"{int(row['count']):,}",
                sub="transactions",
                badge=f"{pct:.2f}%",
                badge_style="blue",
                accent=accent_cycle[i % len(accent_cycle)],
            )

    st.markdown('<div class="section-header">Volume Breakdown</div>', unsafe_allow_html=True)

    ch1, ch2 = st.columns([1, 1])

    with ch1:
        # Donut
        fig_donut = go.Figure(go.Pie(
            labels=df["proxy_type"],
            values=df["count"],
            hole=0.6,
            marker=dict(
                colors=CHART_PALETTE[:len(df)],
                line=dict(color=BG_CARD, width=3),
            ),
            textinfo="label+percent",
            textfont=dict(color="#e6edf3", size=12),
            hovertemplate="<b>%{label}</b><br>Count: %{value:,}<br>Share: %{percent}<extra></extra>",
        ))
        _apply_dark_layout(
            fig_donut,
            title="Proxy Type Share",
            showlegend=False,
            height=320,
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with ch2:
        # Horizontal bar
        fig_bar = go.Figure(go.Bar(
            x=df["count"],
            y=df["proxy_type"],
            orientation="h",
            marker=dict(
                color=CHART_PALETTE[:len(df)],
                line=dict(color=BG_BORDER, width=0.5),
            ),
            text=df["count"].apply(lambda v: f"{int(v):,}"),
            textposition="outside",
            textfont=dict(color=COLOR_NEUTRAL, size=12),
            hovertemplate="<b>%{y}</b><br>Count: %{x:,}<extra></extra>",
        ))
        _apply_dark_layout(
            fig_bar,
            title="Transaction Count by Proxy Type",
            xaxis=dict(**_PLOTLY_BASE["xaxis"], title="Count"),
            yaxis=dict(**_PLOTLY_BASE["yaxis"], title=""),
            height=320,
            margin=dict(l=100, r=80, t=50, b=40),
        )
        st.plotly_chart(fig_bar, use_container_width=True)


def render_hourly_proxy() -> None:
    """Hourly by Proxy page: grouped bar chart."""
    st.markdown('<div class="section-header">Hourly Volume by Proxy Type</div>', unsafe_allow_html=True)

    try:
        data = fetch("/api/hourly-proxy")
    except Exception:
        st.error("Backend unavailable — is FastAPI running on port 8000?")
        return

    if data is None:
        return
    if not data:
        st.info("No hourly proxy data available.")
        return

    df = pd.DataFrame(data)
    proxy_types = sorted(df["proxy_type"].unique()) if "proxy_type" in df.columns else []

    fig = go.Figure()
    for i, proxy_type in enumerate(proxy_types):
        subset = df[df["proxy_type"] == proxy_type].sort_values("hour")
        color = CHART_PALETTE[i % len(CHART_PALETTE)]
        fig.add_trace(go.Bar(
            x=subset["hour"],
            y=subset["count"],
            name=proxy_type,
            marker=dict(color=color, line=dict(color=BG_CARD, width=0.8)),
            hovertemplate=f"<b>{proxy_type}</b><br>Hour: %{{x}}:00<br>Count: %{{y:,}}<extra></extra>",
        ))

    _apply_dark_layout(
        fig,
        title="Hourly Transaction Count by Proxy Type",
        xaxis=dict(
            **_PLOTLY_BASE["xaxis"],
            title="Hour of Day",
            tickmode="linear",
            tick0=0, dtick=1,
        ),
        yaxis=dict(**_PLOTLY_BASE["yaxis"], title="Transaction Count"),
        barmode="group",
        bargap=0.2,
        bargroupgap=0.05,
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(
        page_title="PromptPay Monitoring Dashboard",
        page_icon="💳",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _inject_css()

    # ── Sidebar ──────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(
            f"""
            <div style="padding: 0.5rem 0 1.2rem 0;">
                <div style="font-size:1.3rem; font-weight:700; color:#e6edf3;">
                    💳 PromptPay
                </div>
                <div style="font-size:0.72rem; color:{COLOR_NEUTRAL};
                            text-transform:uppercase; letter-spacing:0.1em;
                            margin-top:0.15rem;">
                    Monitoring Dashboard
                </div>
            </div>
            <div style="border-top:1px solid {BG_BORDER}; margin-bottom:1rem;"></div>
            """,
            unsafe_allow_html=True,
        )

        page = st.radio(
            "NAVIGATION",
            options=[
                "📊  Overview",
                "📈  Hourly Volume",
                "📉  7-Day Trend",
                "🔢  Response Codes",
                "🔵  Proxy Type",
                "⏱  Hourly by Proxy",
            ],
            label_visibility="visible",
        )

        st.markdown(
            f"""
            <div style="border-top:1px solid {BG_BORDER}; margin-top:1.5rem;
                        padding-top:1rem;">
                <div style="font-size:0.68rem; color:{COLOR_NEUTRAL};">
                    Data refreshes every 60 s<br>
                    Backend: <code style="color:{ACCENT_BLUE};">localhost:8000</code>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Backend health indicator ──────────────────────────────────────
        st.markdown(f'<div style="margin-top:0.8rem;"></div>', unsafe_allow_html=True)
        health = fetch("/api/health")
        if health and health.get("status") == "ok":
            st.markdown(
                f'<div style="font-size:0.72rem; color:{COLOR_SUCCESS};">● Backend online</div>',
                unsafe_allow_html=True,
            )
        else:
            err = (health or {}).get("error", "unreachable")
            st.markdown(
                f'<div style="font-size:0.72rem; color:{COLOR_DANGER};">● Backend: {err}</div>',
                unsafe_allow_html=True,
            )

        # ── Cache clear button ────────────────────────────────────────────
        if st.button("🔄 Refresh data", use_container_width=True):
            _fetch_cached.clear()
            st.rerun()

    # ── Page header ───────────────────────────────────────────────────────
    page_titles = {
        "📊  Overview":        ("📊 Overview",               "Real-time KPIs and transaction health"),
        "📈  Hourly Volume":   ("📈 Hourly Volume",           "Transaction volume breakdown by hour and type"),
        "📉  7-Day Trend":     ("📉 7-Day Trend",             "Daily volume trend over the last 7 days"),
        "🔢  Response Codes":  ("🔢 Response Code Summary",   "TSC response code frequency analysis"),
        "🔵  Proxy Type":      ("🔵 Proxy Type Distribution", "Volume split by PromptPay proxy identifier"),
        "⏱  Hourly by Proxy": ("⏱ Hourly by Proxy",         "Hourly breakdown per proxy type"),
    }
    title, subtitle = page_titles.get(page, (page, ""))
    st.markdown(
        f"""
        <div style="margin-bottom:1.2rem;">
            <h1 style="margin-bottom:0.1rem;">{title}</h1>
            <div style="font-size:0.85rem; color:{COLOR_NEUTRAL};">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Route ─────────────────────────────────────────────────────────────
    if page == "📊  Overview":
        render_overview()
    elif page == "📈  Hourly Volume":
        render_hourly_volume()
    elif page == "📉  7-Day Trend":
        render_trend()
    elif page == "🔢  Response Codes":
        render_response_codes()
    elif page == "🔵  Proxy Type":
        render_proxy_type()
    elif page == "⏱  Hourly by Proxy":
        render_hourly_proxy()


if __name__ == "__main__":
    main()
