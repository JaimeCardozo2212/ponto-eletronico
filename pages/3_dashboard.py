"""
Página 3 — Dashboard
Analytics with summary cards, charts, and visual reminders.
Filterable by company and project (multi-select); all metrics/charts
reflect the ALLOCATED hours for the selected companies/projects.
"""

import streamlit as st
from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from database import (
    get_projects,
    get_companies,
    get_allocations_detailed,
)
from utils import (
    format_hours,
    float_to_hours_minutes,
    get_expected_hours_for_period,
    has_entry_today,
    date_range_this_week,
    date_range_this_month,
    get_weekday_name,
    get_setting,
)

st.title("📊 Dashboard")
st.caption("Visão geral das horas alocadas — use os filtros para focar em empresas/projetos")

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

today = date.today()
week_start, week_end = date_range_this_week(today)
month_start, month_end = date_range_this_month(today)
daily_hours = float(get_setting("daily_hours", "8"))

# ═══════════════════════════════════════════════
# FILTROS
# ═══════════════════════════════════════════════
st.subheader("🔎 Filtros")

all_companies = get_companies(active_only=False)
all_projects = get_projects(active_only=False)
company_id_by_name = {c["name"]: c["id"] for c in all_companies}
project_id_by_name = {p["name"]: p["id"] for p in all_projects}

col_f1, col_f2, col_f3 = st.columns([3, 3, 3])
with col_f1:
    chart_period = st.selectbox(
        "📅 Período",
        ["Últimos 7 dias", "Últimos 14 dias", "Últimos 30 dias", "Este mês"],
        index=3,
        key="chart_period",
    )
with col_f2:
    sel_companies = st.multiselect(
        "🏢 Empresas",
        list(company_id_by_name.keys()),
        placeholder="Todas as empresas",
    )
with col_f3:
    sel_projects = st.multiselect(
        "📁 Projetos",
        list(project_id_by_name.keys()),
        placeholder="Todos os projetos",
    )

st.caption("Deixe um filtro vazio para incluir tudo. As horas exibidas são as **alocadas** aos itens selecionados.")

# Resolve filters (empty = no restriction)
company_ids = [company_id_by_name[n] for n in sel_companies] or None
project_ids = [project_id_by_name[n] for n in sel_projects] or None

# Resolve the selected period range
period_days = {"Últimos 7 dias": 7, "Últimos 14 dias": 14, "Últimos 30 dias": 30}
if chart_period == "Este mês":
    c_start, c_end = month_start, today
else:
    days = period_days.get(chart_period, 7)
    c_start = today - timedelta(days=days - 1)
    c_end = today


def alloc_total(start_d: date, end_d: date) -> float:
    """Sum of filtered allocated hours in a date range."""
    rows = get_allocations_detailed(start_d, end_d, company_ids, project_ids)
    return sum(a["hours"] for a in rows)


# Filtered allocations for the selected period (reused by charts)
period_allocs = get_allocations_detailed(c_start, c_end, company_ids, project_ids)

# ═══════════════════════════════════════════════
# CARDS DE RESUMO (alocadas, filtradas)
# ═══════════════════════════════════════════════
st.subheader("📌 Resumo")

hours_today = alloc_total(today, today)
hours_week = alloc_total(week_start, week_end)
hours_period = sum(a["hours"] for a in period_allocs)
n_projects = len({a["project_id"] for a in period_allocs})

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">⏱️ Horas Hoje (alocadas)</div>
        <div class="value">{format_hours(hours_today)}</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">📅 Horas na Semana (alocadas)</div>
        <div class="value">{format_hours(hours_week)}</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">📊 Horas no Período (alocadas)</div>
        <div class="value">{format_hours(hours_period)}</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">📁 Projetos no Período</div>
        <div class="value">{n_projects}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════
# Gráfico: horas alocadas por dia
# ═══════════════════════════════════════════════
st.subheader("📈 Horas Alocadas por Dia")

daily_data: dict[str, dict] = {}
d = c_start
while d <= c_end:
    daily_data[d.isoformat()] = {"date": d, "hours": 0.0, "weekday": get_weekday_name(d)}
    d += timedelta(days=1)

for a in period_allocs:
    ed = a["entry_date"]
    if ed in daily_data:
        daily_data[ed]["hours"] += a["hours"]

df_daily = pd.DataFrame(daily_data.values())

if df_daily["hours"].sum() == 0:
    st.info("Sem horas alocadas no período/filtros selecionados.")
else:
    fig_bar = px.bar(
        df_daily,
        x="date",
        y="hours",
        text=df_daily["hours"].apply(format_hours),
        labels={"date": "Data", "hours": "Horas Alocadas"},
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

# ═══════════════════════════════════════════════
# Pizzas: distribuição por projeto / empresa
# ═══════════════════════════════════════════════
col_left, col_right = st.columns(2)


def summarize(rows, name_key, color_key):
    """Aggregate filtered allocations into [{name, color, total_hours}]."""
    agg: dict[str, dict] = {}
    for a in rows:
        name = a.get(name_key) or "— Sem empresa —"
        color = a.get(color_key) or "#888888"
        if name not in agg:
            agg[name] = {"name": name, "color": color, "total_hours": 0.0}
        agg[name]["total_hours"] += a["hours"]
    return sorted(agg.values(), key=lambda x: x["total_hours"], reverse=True)


with col_left:
    st.subheader("🥧 Distribuição por Projeto")
    proj_summary = summarize(period_allocs, "project_name", "project_color")
    if proj_summary:
        df_pie = pd.DataFrame(proj_summary)
        fig_pie = px.pie(
            df_pie, names="name", values="total_hours", color="name",
            color_discrete_sequence=df_pie["color"].tolist(), hole=0.4,
        )
        fig_pie.update_layout(height=380, margin=dict(t=20, b=20), showlegend=True)
        fig_pie.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Sem dados de projetos no período/filtros selecionados.")

with col_right:
    st.subheader("🏢 Distribuição por Empresa")
    comp_summary = summarize(period_allocs, "company_name", "company_color")
    if comp_summary:
        df_comp = pd.DataFrame(comp_summary)
        fig_comp = px.pie(
            df_comp, names="name", values="total_hours", color="name",
            color_discrete_sequence=df_comp["color"].tolist(), hole=0.4,
        )
        fig_comp.update_layout(height=380, margin=dict(t=20, b=20), showlegend=True)
        fig_comp.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.info("Sem dados de empresas no período/filtros selecionados.")

# ═══════════════════════════════════════════════
# Evolução mensal (alocadas) — últimos 6 meses
# ═══════════════════════════════════════════════
st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
st.subheader("📊 Evolução Mensal (alocadas)")

# Build the last 6 months (oldest → newest)
months: list[tuple[int, int]] = []
y, m = today.year, today.month
for _ in range(6):
    months.append((y, m))
    m -= 1
    if m == 0:
        m = 12
        y -= 1
months.reverse()

months_data = []
for (yy, mm) in months:
    m_start = date(yy, mm, 1)
    if mm == 12:
        m_end = date(yy + 1, 1, 1) - timedelta(days=1)
    else:
        m_end = date(yy, mm + 1, 1) - timedelta(days=1)
    if m_end > today:
        m_end = today
    allocated = sum(a["hours"] for a in get_allocations_detailed(m_start, m_end, company_ids, project_ids))
    months_data.append({
        "Mês": m_start.strftime("%b/%Y"),
        "Horas Alocadas": allocated,
        "Horas Esperadas": get_expected_hours_for_period(m_start, m_end),
    })

df_months = pd.DataFrame(months_data)
fig_line = go.Figure()
fig_line.add_trace(go.Scatter(
    x=df_months["Mês"], y=df_months["Horas Alocadas"],
    mode="lines+markers", name="Alocadas",
    line=dict(color="#6366f1", width=3), marker=dict(size=8),
))
fig_line.add_trace(go.Scatter(
    x=df_months["Mês"], y=df_months["Horas Esperadas"],
    mode="lines+markers", name="Esperadas",
    line=dict(color="#f87171", width=2, dash="dash"), marker=dict(size=6),
))
fig_line.update_layout(height=380, margin=dict(t=20, b=20))
st.plotly_chart(fig_line, use_container_width=True)

# ═══════════════════════════════════════════════
# Gauge: horas alocadas no período vs esperadas
# ═══════════════════════════════════════════════
st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
st.subheader("🎯 Horas Alocadas no Período")

expected_period = get_expected_hours_for_period(c_start, c_end)
gauge_h, gauge_m = float_to_hours_minutes(hours_period)
max_gauge = max(hours_period, expected_period, daily_hours) * 1.2 or daily_hours

fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=round(hours_period, 2),
    number=dict(suffix="h", font=dict(size=48)),
    title={"text": f"Alocado: {gauge_h}:{gauge_m:02d} • Esperado: {format_hours(expected_period)}"},
    delta={"reference": round(expected_period, 2),
           "increasing": {"color": "#4ade80"}, "decreasing": {"color": "#f87171"}},
    gauge={
        "axis": {"range": [0, max_gauge], "tickwidth": 1},
        "bar": {"color": "#6366f1"},
        "steps": [
            {"range": [0, expected_period], "color": "rgba(255,255,255,0.1)"},
            {"range": [expected_period, max_gauge], "color": "rgba(255,255,255,0.05)"},
        ],
        "threshold": {
            "line": {"color": "white", "width": 3},
            "thickness": 0.75,
            "value": expected_period,
        },
    },
))
fig_gauge.update_layout(height=280, margin=dict(t=40, b=20))
st.plotly_chart(fig_gauge, use_container_width=True)
