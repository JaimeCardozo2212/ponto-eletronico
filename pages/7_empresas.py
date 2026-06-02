"""
Página 7 — Empresas
CRUD for companies with color picker and statistics.
"""

import streamlit as st
from database import (
    get_companies,
    create_company,
    update_company,
    toggle_company_active,
    get_company_hours_total,
)
from utils import format_hours

st.title("🏢 Empresas")
st.caption("Gerencie as empresas e veja as horas alocadas a cada uma")

# ── Initialize session state ──
if "edit_company_id" not in st.session_state:
    st.session_state.edit_company_id = None
if "new_company_success" not in st.session_state:
    st.session_state.new_company_success = False


def add_company_callback():
    """Called when the 'Criar Empresa' button is clicked."""
    name = st.session_state.new_comp_name.strip()
    desc = st.session_state.new_comp_desc.strip()
    color = st.session_state.new_comp_color

    if not name:
        st.session_state.new_company_error = "Nome da empresa é obrigatório."
        return

    # Check duplicate
    existing = [c for c in get_companies() if c["name"].lower() == name.lower()]
    if existing:
        st.session_state.new_company_error = f"Já existe uma empresa com o nome '{name}'."
        return

    create_company(name, desc, color)
    st.session_state.new_company_error = ""
    st.session_state.new_company_success = name
    # Clear the input fields
    st.session_state.new_comp_name = ""
    st.session_state.new_comp_desc = ""
    st.session_state.new_comp_color = "#2ca02c"


def edit_company_callback():
    """Called when saving edited company."""
    cid = st.session_state.edit_company_id
    name = st.session_state.edit_comp_name.strip()
    desc = st.session_state.edit_comp_desc.strip()
    color = st.session_state.edit_comp_color

    if not name:
        st.error("Nome da empresa é obrigatório.")
        return

    update_company(cid, name, desc, color)
    st.session_state.edit_company_id = None
    st.rerun()


# ── Success message ──
if st.session_state.new_company_success:
    st.success(f"✅ Empresa '{st.session_state.new_company_success}' criada com sucesso!")
    st.session_state.new_company_success = False

# ── Section 1: New Company ──
st.subheader("➕ Nova Empresa")

# Initialize session keys for new company inputs
if "new_comp_name" not in st.session_state:
    st.session_state.new_comp_name = ""
if "new_comp_desc" not in st.session_state:
    st.session_state.new_comp_desc = ""
if "new_comp_color" not in st.session_state:
    st.session_state.new_comp_color = "#2ca02c"
if "new_company_error" not in st.session_state:
    st.session_state.new_company_error = ""

col_a, col_b, col_c = st.columns([2, 3, 1])
with col_a:
    st.text_input(
        "Nome da Empresa *",
        key="new_comp_name",
        placeholder="Ex: Padaria do Zé",
        label_visibility="visible",
    )
with col_b:
    st.text_input(
        "Descrição",
        key="new_comp_desc",
        placeholder="Descreva a empresa (opcional)...",
        label_visibility="visible",
    )
with col_c:
    st.color_picker(
        "Cor",
        key="new_comp_color",
        label_visibility="visible",
    )

if st.session_state.new_company_error:
    st.error(st.session_state.new_company_error)

st.button(
    "💾 Criar Empresa",
    on_click=add_company_callback,
    type="primary",
    use_container_width=True,
)

# ── Edit Company Section (conditional) ──
edit_id = st.session_state.edit_company_id
if edit_id is not None:
    comp = next((c for c in get_companies() if c["id"] == edit_id), None)
    if comp:
        st.markdown("---")
        st.subheader(f"✏️ Editar: {comp['name']}")

        # Init edit session keys
        if "edit_comp_name" not in st.session_state or st.session_state.get("_last_edit_comp_id") != edit_id:
            st.session_state.edit_comp_name = comp["name"]
            st.session_state.edit_comp_desc = comp.get("description", "")
            st.session_state.edit_comp_color = comp.get("color", "#2ca02c")
            st.session_state._last_edit_comp_id = edit_id

        col_a, col_b, col_c = st.columns([2, 3, 1])
        with col_a:
            st.text_input(
                "Nome da Empresa *",
                key="edit_comp_name",
                label_visibility="visible",
            )
        with col_b:
            st.text_input(
                "Descrição",
                key="edit_comp_desc",
                label_visibility="visible",
            )
        with col_c:
            st.color_picker(
                "Cor",
                key="edit_comp_color",
                label_visibility="visible",
            )

        col_save, col_cancel = st.columns([1, 1])
        with col_save:
            st.button("💾 Salvar Alterações", on_click=edit_company_callback, type="primary")
        with col_cancel:
            if st.button("❌ Cancelar"):
                st.session_state.edit_company_id = None
                st.rerun()
    else:
        st.session_state.edit_company_id = None
        st.rerun()

# ── Section 2: Company List ──
st.markdown("---")
st.subheader("📑 Empresas Cadastradas")

show_inactive = st.checkbox("Mostrar empresas inativas", value=False)
companies = get_companies(active_only=not show_inactive)

if not companies:
    st.info("Nenhuma empresa cadastrada. Use o formulário acima para criar a primeira.")
else:
    # Render as a grid of cards
    cols = st.columns(3)
    for i, comp in enumerate(companies):
        col = cols[i % 3]
        with col:
            total_hours = get_company_hours_total(comp["id"])
            is_active = comp["active"]
            border_color = comp["color"]

            status_badge = ""
            if not is_active:
                status_badge = '<span style="color: #f87171; font-size: 0.75rem; margin-left: 6px;">(Inativa)</span>'

            desc_text = comp["description"] or "Sem descrição"
            # Escape HTML in user-provided text
            safe_name = comp["name"].replace("<", "&lt;").replace(">", "&gt;")
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
                if st.button("✏️ Editar", key=f"ec_{comp['id']}"):
                    st.session_state.edit_company_id = comp["id"]
                    st.rerun()
            with c2:
                if is_active:
                    if st.button("📦 Arquivar", key=f"tc_{comp['id']}"):
                        toggle_company_active(comp["id"], False)
                        st.rerun()
                else:
                    if st.button("✅ Ativar", key=f"tc_{comp['id']}"):
                        toggle_company_active(comp["id"], True)
                        st.rerun()
