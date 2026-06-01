"""
Página 3 — Dashboard
Analytics with summary cards, charts, and visual reminders.
"""

import streamlit as st
from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from database import get_time_entries, get_projects, get_allocations_summary, get_allocations_for_entry
from utils import (
    calculate_worked_hours,
    parse_time,
    format_hours,
    float_to_hours_minutes,
    get_daily_hours_with_projects,
    calculate_hours_balance,
    get_expected_hours_for_period,
    has_entry_today,
    date_range_this_week,
    date_range_this_month,
    get_weekday_name,
    count_business_days_range,
    get_setting,
)

st.title("📊 Dashboard")
st.caption("Visão geral das suas horas e projetos")

# ── Reminders / Alertas ──
has_entry, has_exit = has_entry_today()
if not has_entry:
    st.markdown("""
    <div class="alert-box alert-warning">
        ⚠️ Você ainda não registrou o ponto hoje!
        <a href="?page=registro">Ir para Registrar Ponto →</a>
    </div>
    """, unsafe_allow_html=True)
elif not has_exit:
    st.markdown("""
    <div class="alert-box alert-info">
        ℹ️ Você registrou entrada hoje, mas ainda não registrou a saída. Não esqueça!
    </div>
    """, unsafe_allow_html=True)

# ── Summary Cards ──
st.subheader("📌 Resumo")
today = date.today()
week_start, week_end = date_range_this_week(today)
month_start, month_end = date_range_this_month(today)

# Today's hours
today_entries = get_time_entries(today, today, order_desc=False)
hours_today = sum(
    calculate_worked_hours(
        parse_time(e["start_time"]),
        parse_time(e["lunch_start"]),
        parse_time(e["lunch_end"]),
        parse_time(e["end_time"]),
    )
    for e in today_entries
)

# Week's hours
week_entries = get_time_entries(week_start, week_end, order_desc=False)
hours_week = sum(
    calculate_worked_hours(
        parse_time(e["start_time"]),
        parse_time(e["lunch_start"]),
        parse_time(e["lunch_end"]),
        parse_time(e["end_time"]),
    )
    for e in week_entries
)

# Month's balance
balance_month = calculate_hours_balance(month_start, month_end)
daily_hours = float(get_setting("daily_hours", "8"))
nb_projects = len(get_projects(active_only=True))

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">⏱️ Horas Hoje</div>
        <div class="value">{format_hours(hours_today)}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">📅 Horas na Semana</div>
        <div class="value">{format_hours(hours_week)}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    bal_str = f"+{format_hours(abs(balance_month))}" if balance_month >= 0 else f"-{format_hours(abs(balance_month))}"
    bal_class = "positive" if balance_month >= 0 else "negative"
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">🏦 Banco de Horas (Mês)</div>
        <div class="value {bal_class}">{bal_str}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">📁 Projetos Ativos</div>
        <div class="value">{nb_projects}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# ── Charts Row 1 ──
st.subheader("📈 Horas Trabalhadas")
chart_period = st.radio(
    "Período",
    ["Últimos 7 dias", "Últimos 14 dias", "Últimos 30 dias", "Este mês"],
    key="chart_period",
    horizontal=True,
)

period_days = {"Últimos 7 dias": 7, "Últimos 14 dias": 14, "Últimos 30 dias": 30}
if chart_period == "Este mês":
    c_start, c_end = month_start, month_end
else:
    days = period_days.get(chart_period, 7)
    c_start = today - timedelta(days=days - 1)
    c_end = today

entries = get_time_entries(c_start, c_end, order_desc=False)

# Build daily hours data
daily_data: dict[str, dict] = {}
d = c_start
while d <= c_end:
    daily_data[d.isoformat()] = {"date": d, "hours": 0.0, "weekday": get_weekday_name(d)}
    d += timedelta(days=1)

for entry in entries:
    ed = entry["date"]
    if ed in daily_data:
        worked = calculate_worked_hours(
            parse_time(entry["start_time"]),
            parse_time(entry["lunch_start"]),
            parse_time(entry["lunch_end"]),
            parse_time(entry["end_time"]),
        )
        daily_data[ed]["hours"] += worked

df_daily = pd.DataFrame(daily_data.values())

# Bar chart
fig_bar = px.bar(
    df_daily,
    x="date",
    y="hours",
    text=df_daily["hours"].apply(format_hours),
    labels={"date": "Data", "hours": "Horas"},
    color_discrete_sequence=["#6366f1"],
)
fig_bar.add_hline(
    y=daily_hours,
    line_dash="dash",
    line_color="#f87171",
    annotation_text=f"Meta: {format_hours(daily_hours)}/dia",
)
fig_bar.update_traces(textposition="outside")
fig_bar.update_layout(height=380, margin=dict(t=20, b=20), hovermode="x")
st.plotly_chart(fig_bar, use_container_width=True)

# ── Charts Row 2 ──
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🥧 Distribuição por Projeto")
    proj_summary = get_allocations_summary(c_start, c_end)
    if proj_summary:
        df_pie = pd.DataFrame(proj_summary)
        fig_pie = px.pie(
            df_pie,
            names="name",
            values="total_hours",
            color="name",
            color_discrete_sequence=df_pie["color"].tolist() if "color" in df_pie else None,
            hole=0.4,
        )
        fig_pie.update_layout(height=380, margin=dict(t=20, b=20), showlegend=True)
        fig_pie.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Sem dados de projetos no período selecionado.")

with col_right:
    st.subheader("📊 Evolução Mensal")
    # Monthly evolution for the last 6 months
    months_data = []
    for i in range(5, -1, -1):
        m_date = today.replace(day=1) - timedelta(days=1)
        for _ in range(i):
            m_date = m_date.replace(day=1) - timedelta(days=1)
        m_year = m_date.year if i > 0 else today.year
        m_month = m_date.month if i > 0 else today.month
        m_start = date(today.year if i > 0 or m_month <= today.month else today.year, m_month, 1)
        # Recalculate correctly
        if i == 0:
            m_start = date(today.year, today.month, 1)
            m_end = today
        else:
            ref = today.replace(day=1) - timedelta(days=i * 28)
            m_start = ref.replace(day=1)
            if m_start.month == 12:
                m_end = date(m_start.year + 1, 1, 1) - timedelta(days=1)
            else:
                m_end = m_start.replace(month=m_start.month + 1, day=1) - timedelta(days=1)

        m_entries = get_time_entries(m_start, m_end, order_desc=False)
        m_hours = sum(
            calculate_worked_hours(
                parse_time(e["start_time"]),
                parse_time(e["lunch_start"]),
                parse_time(e["lunch_end"]),
                parse_time(e["end_time"]),
            )
            for e in m_entries
        )
        months_data.append({
            "Mês": m_start.strftime("%b/%Y"),
            "Horas Trabalhadas": m_hours,
            "Horas Esperadas": get_expected_hours_for_period(m_start, m_end),
        })

    df_months = pd.DataFrame(months_data)
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=df_months["Mês"], y=df_months["Horas Trabalhadas"],
        mode="lines+markers", name="Trabalhadas",
        line=dict(color="#6366f1", width=3),
        marker=dict(size=8),
    ))
    fig_line.add_trace(go.Scatter(
        x=df_months["Mês"], y=df_months["Horas Esperadas"],
        mode="lines+markers", name="Esperadas",
        line=dict(color="#f87171", width=2, dash="dash"),
        marker=dict(size=6),
    ))
    fig_line.update_layout(height=380, margin=dict(t=20, b=20))
    st.plotly_chart(fig_line, use_container_width=True)

# ── Gauge: Banco de Horas ──
st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
st.subheader("🏦 Banco de Horas — Saldo do Mês")

bal_h, bal_m = float_to_hours_minutes(abs(balance_month))
bal_sign = "+" if balance_month >= 0 else "-"
max_gauge = max(abs(balance_month) + 10, daily_hours * 2)

fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=abs(balance_month),
    number=dict(suffix="h", font=dict(size=48)),
    title={"text": f"Saldo: {bal_sign}{bal_h}:{bal_m:02d}"},
    delta={"reference": daily_hours, "increasing": {"color": "#4ade80"}, "decreasing": {"color": "#f87171"}},
    gauge={
        "axis": {"range": [0, max_gauge], "tickwidth": 1},
        "bar": {"color": "#4ade80" if balance_month >= 0 else "#f87171"},
        "steps": [
            {"range": [0, daily_hours], "color": "rgba(255,255,255,0.1)"},
            {"range": [daily_hours, max_gauge], "color": "rgba(255,255,255,0.05)"},
        ],
        "threshold": {
            "line": {"color": "white", "width": 3},
            "thickness": 0.75,
            "value": daily_hours,
        },
    },
))
fig_gauge.update_layout(height=280, margin=dict(t=40, b=20))
st.plotly_chart(fig_gauge, use_container_width=True)
