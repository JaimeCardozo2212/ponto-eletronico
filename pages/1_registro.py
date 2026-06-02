"""
Página 1 — Registrar Ponto
Daily time entry with project allocation and validation.
"""

import streamlit as st
from datetime import date, time
from database import (
    create_time_entry,
    update_time_entry,
    delete_time_entry,
    get_time_entry,
    get_time_entries,
    get_projects,
    get_companies,
    create_allocation,
    delete_allocations_for_entry,
    get_allocations_for_entry,
)
from utils import (
    parse_time,
    calculate_worked_hours,
    format_hours,
    get_daily_hours_with_projects,
    get_weekday_name,
)
import pandas as pd

st.title(":white_check_mark: Registrar Ponto")
st.caption("Registre suas horas trabalhadas e vincule a projetos")

# ── Initialize session state ──
if "editing_entry_id" not in st.session_state:
    st.session_state.editing_entry_id = None
if "allocations_data" not in st.session_state:
    st.session_state.allocations_data = []  # list of (company_id, project_id, hours, notes)
if "reg_save_triggered" not in st.session_state:
    st.session_state.reg_save_triggered = False
if "reg_success_msg" not in st.session_state:
    st.session_state.reg_success_msg = ""
if "reg_deleted_msg" not in st.session_state:
    st.session_state.reg_deleted_msg = ""

# ── Show pending messages ──
if st.session_state.reg_success_msg:
    st.success(st.session_state.reg_success_msg)
    st.session_state.reg_success_msg = ""
if st.session_state.reg_deleted_msg:
    st.success(st.session_state.reg_deleted_msg)
    st.session_state.reg_deleted_msg = ""


def clear_form_state():
    """Reset all form-related session state."""
    st.session_state.editing_entry_id = None
    st.session_state.allocations_data = []
    st.session_state.reg_save_triggered = False
    # Clear pre-fill keys
    for key in ["reg_date", "reg_start", "reg_lunch_s", "reg_lunch_e", "reg_end", "reg_notes"]:
        st.session_state.pop(key, None)
    # Clear stale allocation widget keys
    keys_to_pop = [k for k in st.session_state if k.startswith(("pa_comp_", "pa_proj_", "pa_hrs_", "pa_note_", "pa_rm_"))]
    for k in keys_to_pop:
        st.session_state.pop(k, None)


def load_entry_for_edit(entry_id: int):
    """Pre-fill the form for editing an existing entry."""
    entry = get_time_entry(entry_id)
    allocs = get_allocations_for_entry(entry_id)

    st.session_state.editing_entry_id = entry_id
    st.session_state.allocations_data = [
        (a.get("company_id"), a["project_id"], a["hours"], a.get("notes", "")) for a in allocs
    ]
    st.session_state.reg_date = (
        date.fromisoformat(entry["date"]) if entry["date"] else date.today()
    )
    st.session_state.reg_start = parse_time(entry["start_time"]) or time(8, 0)
    st.session_state.reg_lunch_s = parse_time(entry["lunch_start"]) or time(12, 0)
    st.session_state.reg_lunch_e = parse_time(entry["lunch_end"]) or time(13, 0)
    st.session_state.reg_end = parse_time(entry["end_time"]) or time(17, 0)
    st.session_state.reg_notes = entry["notes"] or ""


def add_allocation_callback():
    """Add a new empty allocation row."""
    projects = get_projects(active_only=True)
    if not projects:
        st.warning("Cadastre um projeto primeiro na página 📋 Projetos")
        return
    companies = get_companies(active_only=True)
    default_company = companies[0]["id"] if companies else None
    st.session_state.allocations_data.append((default_company, projects[0]["id"], 0.0, ""))


def remove_allocation_callback(idx: int):
    """Remove an allocation row by index and clean widget keys."""
    if 0 <= idx < len(st.session_state.allocations_data):
        st.session_state.allocations_data.pop(idx)
        # Clear all allocation widget keys so values reload from allocations_data
        keys_to_pop = [
            k for k in list(st.session_state.keys())
            if k.startswith(("pa_comp_", "pa_proj_", "pa_hrs_", "pa_note_", "pa_rm_"))
        ]
        for k in keys_to_pop:
            st.session_state.pop(k, None)


def save_entry_callback():
    """Process the save (create or update). Triggered by form submit."""
    st.session_state.reg_save_triggered = True


# ── Determine mode ──
editing = st.session_state.editing_entry_id is not None

# ── Set default values ──
if editing:
    default_date = st.session_state.get("reg_date", date.today())
    default_start = st.session_state.get("reg_start", time(8, 0))
    default_lunch_s = st.session_state.get("reg_lunch_s", time(12, 0))
    default_lunch_e = st.session_state.get("reg_lunch_e", time(13, 0))
    default_end = st.session_state.get("reg_end", time(17, 0))
    default_notes = st.session_state.get("reg_notes", "")
else:
    default_date = date.today()
    default_start = time(8, 0)
    default_lunch_s = time(12, 0)
    default_lunch_e = time(13, 0)
    default_end = time(17, 0)
    default_notes = ""

# ═══════════════════════════════════════════════
# FORM: Time fields only
# ═══════════════════════════════════════════════

if editing:
    st.info(f"✏️ Editando registro #{st.session_state.editing_entry_id}")

with st.form("time_entry_form", clear_on_submit=False):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        entry_date = st.date_input("📅 Data", value=default_date, format="DD/MM/YYYY")
    with col2:
        start_time = st.time_input("🟢 Entrada", value=default_start, step=300)
    with col3:
        lunch_start = st.time_input("🍽️ Início Almoço", value=default_lunch_s, step=300)
    with col4:
        lunch_end = st.time_input("🍽️ Volta Almoço", value=default_lunch_e, step=300)

    col_a, col_b = st.columns(2)
    with col_a:
        end_time = st.time_input("🔴 Saída Final", value=default_end, step=300)
    with col_b:
        notes = st.text_area("📝 Observações", value=default_notes, height=68)

    # Real-time calculation
    worked = calculate_worked_hours(start_time, lunch_start, lunch_end, end_time)
    st.markdown(f"**⏱️ Horas trabalhadas: `{format_hours(worked)}`**")

    # Submit button (always inside form)
    if editing:
        col_btn, _ = st.columns([2, 8])
        with col_btn:
            form_submitted = st.form_submit_button(
                "💾 Salvar Alterações", type="primary", on_click=save_entry_callback
            )
    else:
        col_btn, _ = st.columns([2, 8])
        with col_btn:
            form_submitted = st.form_submit_button(
                "💾 Salvar Registro", type="primary", on_click=save_entry_callback
            )

# ═══════════════════════════════════════════════
# OUTSIDE FORM: Project Allocations
# ═══════════════════════════════════════════════

st.markdown("---")
st.subheader("📎 Vincular a Projetos")

projects = get_projects(active_only=True)
companies = get_companies(active_only=True)

if not projects:
    st.warning("⚠️ Nenhum projeto ativo. Vá para a página 📋 Projetos e cadastre um projeto primeiro.")
else:
    if not companies:
        st.info("💡 Dica: cadastre empresas na página 🏢 Empresas para vincular as horas a uma empresa.")

    project_names = [p["name"] for p in projects]
    project_id_by_name = {p["name"]: p["id"] for p in projects}

    NO_COMPANY = "— Sem empresa —"
    company_names = [NO_COMPANY] + [c["name"] for c in companies]
    company_id_by_name = {c["name"]: c["id"] for c in companies}
    company_name_by_id = {c["id"]: c["name"] for c in companies}

    # Render each allocation row
    for idx in range(len(st.session_state.allocations_data)):
        company_id, proj_id, hrs, alloc_notes = st.session_state.allocations_data[idx]

        # Ensure proj_id is still valid
        if proj_id not in [p["id"] for p in projects]:
            proj_id = projects[0]["id"]
            st.session_state.allocations_data[idx] = (company_id, proj_id, hrs, alloc_notes)

        proj_name = next((p["name"] for p in projects if p["id"] == proj_id), project_names[0])
        comp_name = company_name_by_id.get(company_id, NO_COMPANY)

        c0, c1, c2, c3, c4 = st.columns([3, 3, 1.5, 3, 1])
        with c0:
            sel_company = st.selectbox(
                f"Empresa #{idx + 1}",
                company_names,
                index=company_names.index(comp_name) if comp_name in company_names else 0,
                key=f"pa_comp_{idx}",
                label_visibility="visible",
            )
        with c1:
            sel_name = st.selectbox(
                f"Projeto #{idx + 1}",
                project_names,
                index=project_names.index(proj_name) if proj_name in project_names else 0,
                key=f"pa_proj_{idx}",
                label_visibility="visible",
            )
        with c2:
            hrs_val = st.number_input(
                "Horas",
                min_value=0.0,
                max_value=24.0,
                value=float(hrs),
                step=0.5,
                key=f"pa_hrs_{idx}",
                label_visibility="visible",
            )
        with c3:
            alloc_note = st.text_input(
                "Nota",
                value=alloc_notes,
                key=f"pa_note_{idx}",
                placeholder="Opcional",
                label_visibility="visible",
            )
        with c4:
            st.markdown("<br>", unsafe_allow_html=True)
            st.button(
                "🗑️",
                key=f"pa_rm_{idx}",
                on_click=remove_allocation_callback,
                args=(idx,),
            )

        # Update session state from widget values
        new_proj_id = project_id_by_name.get(sel_name, proj_id)
        new_company_id = company_id_by_name.get(sel_company)  # None for "Sem empresa"
        st.session_state.allocations_data[idx] = (new_company_id, new_proj_id, hrs_val, alloc_note)

    # Add allocation button (outside form)
    st.button(
        "➕ Adicionar Projeto",
        on_click=add_allocation_callback,
        use_container_width=True,
    )

    # Show allocation summary
    if st.session_state.allocations_data:
        total_alloc = sum(h for (_, _, h, _) in st.session_state.allocations_data)
        if total_alloc > 0:
            color = "#f87171" if (worked > 0 and total_alloc > worked) else "#a0a0b8"
            st.caption(f"Total alocado: **{format_hours(total_alloc)}** | Horas trabalhadas: **{format_hours(worked)}**")

# ═══════════════════════════════════════════════
# Edit mode: Cancel button (outside form)
# ═══════════════════════════════════════════════

if editing:
    st.markdown("---")
    if st.button("❌ Cancelar Edição", use_container_width=True):
        clear_form_state()
        st.rerun()

# ═══════════════════════════════════════════════
# Process Save
# ═══════════════════════════════════════════════

if st.session_state.reg_save_triggered:
    st.session_state.reg_save_triggered = False

    # Validate allocations
    total_alloc = sum(h for (_, _, h, _) in st.session_state.allocations_data)
    if total_alloc > worked and worked > 0:
        st.error(
            f"⚠️ Total alocado aos projetos ({format_hours(total_alloc)}) "
            f"excede horas trabalhadas ({format_hours(worked)})!"
        )
    elif worked <= 0:
        st.error("⚠️ Preencha todos os horários (entrada, almoço e saída).")
    else:
        if editing:
            update_time_entry(
                st.session_state.editing_entry_id,
                entry_date, start_time, lunch_start, lunch_end, end_time, notes,
            )
            delete_allocations_for_entry(st.session_state.editing_entry_id)
            entry_id = st.session_state.editing_entry_id
        else:
            entry_id = create_time_entry(
                entry_date, start_time, lunch_start, lunch_end, end_time, notes,
            )

        # Save allocations
        for (comp_id, proj_id, hrs, alloc_notes) in st.session_state.allocations_data:
            if hrs > 0:
                create_allocation(entry_id, proj_id, hrs, alloc_notes, company_id=comp_id)

        if editing:
            st.session_state.reg_success_msg = f"✅ Registro #{entry_id} atualizado!"
        else:
            st.session_state.reg_success_msg = f"✅ Registro #{entry_id} salvo!"

        clear_form_state()
        st.rerun()

# ═══════════════════════════════════════════════
# Today's entries
# ═══════════════════════════════════════════════

st.markdown("---")
st.subheader(
    f"📋 Registros de Hoje — {date.today().strftime('%d/%m/%Y')} "
    f"({get_weekday_name(date.today())})"
)

today_entries = get_time_entries(date.today(), date.today(), order_desc=False)

if not today_entries:
    st.info("Nenhum registro hoje ainda. Use o formulário acima para registrar seu ponto.")
else:
    enriched = [get_daily_hours_with_projects(e) for e in today_entries]
    df_data = []
    for e in enriched:
        df_data.append({
            "ID": e["id"],
            "Entrada": e["start_time"] or "—",
            "Início Almoço": e["lunch_start"] or "—",
            "Volta Almoço": e["lunch_end"] or "—",
            "Saída": e["end_time"] or "—",
            "Horas": e["worked_hours_str"],
            "Empresas": e["company_names"],
            "Projetos": e["project_names"],
            "Obs": (e["notes"] or "—")[:60],
        })

    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    total_today = sum(e["worked_hours"] for e in enriched)
    st.markdown(f"**Total hoje: {format_hours(total_today)}**")

    # Quick actions
    st.markdown("---")
    st.caption("Ações rápidas:")
    for entry_row in enriched:
        c1, c2, _ = st.columns([1, 1, 6])
        with c1:
            if st.button(f"✏️ Editar #{entry_row['id']}", key=f"qedit_{entry_row['id']}"):
                load_entry_for_edit(entry_row["id"])
                st.rerun()
        with c2:
            if st.button(f"🗑️ Excluir #{entry_row['id']}", key=f"qdel_{entry_row['id']}"):
                delete_time_entry(entry_row["id"])
                st.session_state.reg_deleted_msg = f"Registro #{entry_row['id']} excluído."
                clear_form_state()
                st.rerun()
