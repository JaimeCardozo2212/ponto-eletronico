"""
Página 2 — Projetos
CRUD for projects with color picker and statistics.
"""

import streamlit as st
from database import (
    get_projects,
    create_project,
    update_project,
    toggle_project_active,
    get_project_hours_total,
)
from utils import format_hours

st.title("📋 Projetos")
st.caption("Gerencie seus projetos e veja as horas alocadas")

# ── Initialize session state ──
if "edit_project_id" not in st.session_state:
    st.session_state.edit_project_id = None
if "new_project_success" not in st.session_state:
    st.session_state.new_project_success = False


def add_project_callback():
    """Called when the 'Criar Projeto' button is clicked."""
    name = st.session_state.new_proj_name.strip()
    desc = st.session_state.new_proj_desc.strip()
    color = st.session_state.new_proj_color

    if not name:
        st.session_state.new_project_error = "Nome do projeto é obrigatório."
        return

    # Check duplicate
    existing = [p for p in get_projects() if p["name"].lower() == name.lower()]
    if existing:
        st.session_state.new_project_error = f"Já existe um projeto com o nome '{name}'."
        return

    create_project(name, desc, color)
    st.session_state.new_project_error = ""
    st.session_state.new_project_success = name
    # Clear the input fields
    st.session_state.new_proj_name = ""
    st.session_state.new_proj_desc = ""
    st.session_state.new_proj_color = "#1f77b4"


def edit_project_callback():
    """Called when saving edited project."""
    pid = st.session_state.edit_project_id
    name = st.session_state.edit_proj_name.strip()
    desc = st.session_state.edit_proj_desc.strip()
    color = st.session_state.edit_proj_color

    if not name:
        st.error("Nome do projeto é obrigatório.")
        return

    update_project(pid, name, desc, color)
    st.session_state.edit_project_id = None
    st.rerun()


# ── Success message ──
if st.session_state.new_project_success:
    st.success(f"✅ Projeto '{st.session_state.new_project_success}' criado com sucesso!")
    st.session_state.new_project_success = False

# ── Section 1: New Project ──
st.subheader("➕ Novo Projeto")

# Initialize session keys for new project inputs
if "new_proj_name" not in st.session_state:
    st.session_state.new_proj_name = ""
if "new_proj_desc" not in st.session_state:
    st.session_state.new_proj_desc = ""
if "new_proj_color" not in st.session_state:
    st.session_state.new_proj_color = "#1f77b4"
if "new_project_error" not in st.session_state:
    st.session_state.new_project_error = ""

col_a, col_b, col_c = st.columns([2, 3, 1])
with col_a:
    st.text_input(
        "Nome do Projeto *",
        key="new_proj_name",
        placeholder="Ex: Projeto Alpha",
        label_visibility="visible",
    )
with col_b:
    st.text_input(
        "Descrição",
        key="new_proj_desc",
        placeholder="Descreva o projeto (opcional)...",
        label_visibility="visible",
    )
with col_c:
    st.color_picker(
        "Cor",
        key="new_proj_color",
        label_visibility="visible",
    )

if st.session_state.new_project_error:
    st.error(st.session_state.new_project_error)

st.button(
    "💾 Criar Projeto",
    on_click=add_project_callback,
    type="primary",
    use_container_width=True,
)

# ── Edit Project Section (conditional) ──
edit_id = st.session_state.edit_project_id
if edit_id is not None:
    proj = next((p for p in get_projects() if p["id"] == edit_id), None)
    if proj:
        st.markdown("---")
        st.subheader(f"✏️ Editar: {proj['name']}")

        # Init edit session keys
        if "edit_proj_name" not in st.session_state or st.session_state.get("_last_edit_id") != edit_id:
            st.session_state.edit_proj_name = proj["name"]
            st.session_state.edit_proj_desc = proj.get("description", "")
            st.session_state.edit_proj_color = proj.get("color", "#1f77b4")
            st.session_state._last_edit_id = edit_id

        col_a, col_b, col_c = st.columns([2, 3, 1])
        with col_a:
            st.text_input(
                "Nome do Projeto *",
                key="edit_proj_name",
                label_visibility="visible",
            )
        with col_b:
            st.text_input(
                "Descrição",
                key="edit_proj_desc",
                label_visibility="visible",
            )
        with col_c:
            st.color_picker(
                "Cor",
                key="edit_proj_color",
                label_visibility="visible",
            )

        col_save, col_cancel = st.columns([1, 1])
        with col_save:
            st.button("💾 Salvar Alterações", on_click=edit_project_callback, type="primary")
        with col_cancel:
            if st.button("❌ Cancelar"):
                st.session_state.edit_project_id = None
                st.rerun()
    else:
        st.session_state.edit_project_id = None
        st.rerun()

# ── Section 2: Project List ──
st.markdown("---")
st.subheader("📑 Projetos Cadastrados")

show_inactive = st.checkbox("Mostrar projetos inativos", value=False)
projects = get_projects(active_only=not show_inactive)

if not projects:
    st.info("Nenhum projeto cadastrado. Use o formulário acima para criar o primeiro.")
else:
    # Render as a grid of cards
    cols = st.columns(3)
    for i, proj in enumerate(projects):
        col = cols[i % 3]
        with col:
            total_hours = get_project_hours_total(proj["id"])
            is_active = proj["active"]
            border_color = proj["color"]

            # Build card HTML safely
            status_badge = ""
            if not is_active:
                status_badge = '<span style="color: #f87171; font-size: 0.75rem; margin-left: 6px;">(Inativo)</span>'

            desc_text = proj["description"] or "Sem descrição"
            # Escape HTML in user-provided text
            safe_name = proj["name"].replace("<", "&lt;").replace(">", "&gt;")
            safe_desc = desc_text.replace("<", "&lt;").replace(">", "&gt;")

            # NOTE: HTML lines must NOT be indented. Markdown treats lines
            # indented with 4+ spaces as a code block, which would render the
            # raw HTML as text instead of a card.
            card_html = (
                f'<div style="border-left: 4px solid {border_color}; '
                'border-radius: 8px; padding: 1rem; margin-bottom: 0.8rem; '
                'background: rgba(255,255,255,0.03); min-height: 120px;">'
                '<div style="display: flex; align-items: center; gap: 8px;">'
                f'<span style="width: 14px; height: 14px; border-radius: 50%; '
                f'background: {border_color}; display: inline-block; '
                'flex-shrink: 0;"></span>'
                f'<strong style="font-size: 1rem;">{safe_name}</strong>'
                f'{status_badge}'
                '</div>'
                '<div style="margin-top: 6px; font-size: 0.85rem; '
                f'color: #a0a0b8; min-height: 20px;">{safe_desc}</div>'
                '<div style="margin-top: 8px; font-weight: 600; '
                f'font-size: 1.1rem; color: #e0e0e0;">⏱️ {format_hours(total_hours)}</div>'
                '</div>'
            )

            st.markdown(card_html, unsafe_allow_html=True)

            # Buttons
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✏️ Editar", key=f"e_{proj['id']}"):
                    st.session_state.edit_project_id = proj["id"]
                    st.rerun()
            with c2:
                if is_active:
                    if st.button("📦 Arquivar", key=f"t_{proj['id']}"):
                        toggle_project_active(proj["id"], False)
                        st.rerun()
                else:
                    if st.button("✅ Ativar", key=f"t_{proj['id']}"):
                        toggle_project_active(proj["id"], True)
                        st.rerun()
