"""
Página 4 — Histórico
Filterable history table with edit/delete and aggregated summaries.
"""

import streamlit as st
from datetime import date, datetime
import pandas as pd

from database import (
    get_time_entries,
    get_time_entry,
    get_projects,
    get_companies,
    update_time_entry,
    delete_time_entry,
    delete_allocations_for_entry,
    create_allocation,
    get_allocations_for_entry,
)
from utils import (
    parse_time,
    format_hours,
    get_daily_hours_with_projects,
    get_weekday_name,
)

st.title("📅 Histórico")
st.caption("Visualize, filtre e edite todos os registros")

# ── Filters ──
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    date_range = st.date_input(
        "📅 Período",
        value=(date.today().replace(day=1), date.today()),
        format="DD/MM/YYYY",
    )
with col_f2:
    projects = get_projects(active_only=False)
    project_options = ["Todos"] + [p["name"] for p in projects]
    project_filter = st.selectbox("📁 Projeto", project_options)
with col_f3:
    search_text = st.text_input("🔍 Buscar (observações)", placeholder="Termo de busca...")

# Parse date range
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
elif isinstance(date_range, date):
    start_date = end_date = date_range
else:
    start_date = date.today().replace(day=1)
    end_date = date.today()

# Determine project_id filter
proj_id = None
if project_filter != "Todos":
    proj_id = next((p["id"] for p in projects if p["name"] == project_filter), None)

# Fetch entries
entries = get_time_entries(start_date, end_date, project_id=proj_id, order_desc=True)

# Enrich
enriched = [get_daily_hours_with_projects(e) for e in entries]

# Apply text search
if search_text.strip():
    enriched = [
        e for e in enriched
        if search_text.lower() in (e.get("notes") or "").lower()
        or search_text.lower() in (e.get("project_names") or "").lower()
    ]

st.caption(f"{len(enriched)} registros encontrados")

# ── Data Table ──
if enriched:
    df_data = []
    for e in enriched:
        date_obj = date.fromisoformat(e["date"]) if isinstance(e["date"], str) else e["date"]
        df_data.append({
            "ID": e["id"],
            "Data": date_obj.strftime("%d/%m/%Y"),
            "Dia": get_weekday_name(date_obj),
            "Entrada": e["start_time"] or "—",
            "Início Almoço": e["lunch_start"] or "—",
            "Volta Almoço": e["lunch_end"] or "—",
            "Saída": e["end_time"] or "—",
            "Horas": e["worked_hours_str"],
            "Empresas": e["company_names"],
            "Projetos": e["project_names"],
            "Obs": (e["notes"] or "—")[:50],
        })

    df = pd.DataFrame(df_data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "Data": st.column_config.TextColumn("Data", width="small"),
            "Horas": st.column_config.TextColumn("Horas", width="small"),
        },
    )

    # ── Summary ──
    total_hours = sum(e["worked_hours"] for e in enriched)
    avg_hours = total_hours / len(enriched) if enriched else 0

    st.markdown("---")
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        st.metric("📊 Total de Registros", len(enriched))
    with col_s2:
        st.metric("⏱️ Total de Horas", format_hours(total_hours))
    with col_s3:
        st.metric("📐 Média por Dia", format_hours(avg_hours))

    # ── Edit / Delete Section ──
    st.markdown("---")
    st.subheader("✏️ Editar ou Excluir Registro")

    entry_id_input = st.number_input(
        "ID do registro",
        min_value=1,
        step=1,
        value=None,
        placeholder="Digite o ID...",
        key="hist_entry_id",
    )

    if entry_id_input:
        entry = get_time_entry(entry_id_input)
        if entry:
            allocs = get_allocations_for_entry(entry_id_input)

            with st.form("hist_edit_form"):
                st.info(f"Editando registro #{entry_id_input} — {entry['date']}")

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    new_date = st.date_input(
                        "Data",
                        value=date.fromisoformat(entry["date"]) if entry["date"] else date.today(),
                        format="DD/MM/YYYY",
                    )
                with col2:
                    new_start = st.time_input(
                        "Entrada",
                        value=parse_time(entry["start_time"]) or datetime.now().time(),
                        step=300,
                    )
                with col3:
                    new_lunch_s = st.time_input(
                        "Início Almoço",
                        value=parse_time(entry["lunch_start"]) or datetime.now().time(),
                        step=300,
                    )
                with col4:
                    new_lunch_e = st.time_input(
                        "Volta Almoço",
                        value=parse_time(entry["lunch_end"]) or datetime.now().time(),
                        step=300,
                    )

                col_a, col_b = st.columns(2)
                with col_a:
                    new_end = st.time_input(
                        "Saída",
                        value=parse_time(entry["end_time"]) or datetime.now().time(),
                        step=300,
                    )
                with col_b:
                    new_notes = st.text_area("Observações", value=entry["notes"] or "")

                # Allocations edit
                st.markdown("**Alocações de Projeto:**")
                NO_COMPANY = "— Sem empresa —"
                all_companies = get_companies()
                company_choices = [NO_COMPANY] + [c["name"] for c in all_companies]
                company_map = {c["name"]: c["id"] for c in all_companies}
                company_name_by_id = {c["id"]: c["name"] for c in all_companies}
                proj_names = [p["name"] for p in get_projects()]
                proj_map = {p["name"]: p["id"] for p in get_projects()}
                new_allocs = []
                for i, a in enumerate(allocs):
                    c0, c1, c2, c3 = st.columns([3, 3, 2, 1])
                    with c0:
                        cur_comp = company_name_by_id.get(a.get("company_id"), NO_COMPANY)
                        sel_comp = st.selectbox(
                            f"Empresa #{i+1}",
                            company_choices,
                            index=company_choices.index(cur_comp) if cur_comp in company_choices else 0,
                            key=f"hist_ac_{i}",
                        )
                    with c1:
                        idx = (
                            proj_names.index(a["project_name"])
                            if a["project_name"] in proj_names
                            else 0
                        )
                        sel_proj = st.selectbox(
                            f"Projeto #{i+1}",
                            proj_names,
                            index=idx,
                            key=f"hist_ap_{i}",
                        )
                    with c2:
                        hrs = st.number_input(
                            f"Horas #{i+1}",
                            min_value=0.0,
                            max_value=24.0,
                            value=float(a["hours"]),
                            step=0.5,
                            key=f"hist_ah_{i}",
                        )
                    with c3:
                        st.markdown("<br>", unsafe_allow_html=True)
                        remove = st.checkbox("Remover", key=f"hist_arm_{i}")
                    if not remove:
                        new_allocs.append((
                            company_map.get(sel_comp),
                            proj_map.get(sel_proj, a["project_id"]),
                            hrs,
                            a.get("notes", ""),
                        ))

                col_save, col_del, _ = st.columns([1, 1, 6])
                with col_save:
                    save_btn = st.form_submit_button("💾 Salvar", type="primary")
                with col_del:
                    del_btn = st.form_submit_button("🗑️ Excluir Registro")

            if save_btn:
                update_time_entry(
                    entry_id_input, new_date, new_start,
                    new_lunch_s, new_lunch_e, new_end, new_notes,
                )
                delete_allocations_for_entry(entry_id_input)
                for comp_id, proj_id, hrs, anotes in new_allocs:
                    if hrs > 0:
                        create_allocation(entry_id_input, proj_id, hrs, anotes, company_id=comp_id)
                st.success(f"Registro #{entry_id_input} atualizado!")
                st.rerun()

            if del_btn:
                delete_time_entry(entry_id_input)
                st.success(f"Registro #{entry_id_input} excluído!")
                st.rerun()
        else:
            st.warning(f"Registro #{entry_id_input} não encontrado.")
else:
    st.info("Nenhum registro encontrado para os filtros selecionados.")
