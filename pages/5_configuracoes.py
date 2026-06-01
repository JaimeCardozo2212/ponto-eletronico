"""
Página 5 — Configurações
Settings: daily/weekly hours, holidays management, weekend toggle.
"""

import streamlit as st
from datetime import date
import pandas as pd

from database import (
    get_all_settings,
    set_setting,
    get_holidays,
    create_holiday,
    delete_holiday,
)

st.title("⚙️ Configurações")
st.caption("Ajuste as preferências do sistema")

# ── Initialize session state flags ──
if "settings_saved" not in st.session_state:
    st.session_state.settings_saved = False
if "holiday_added" not in st.session_state:
    st.session_state.holiday_added = ""


def save_settings_callback():
    """Called when 'Salvar Configurações' is clicked."""
    set_setting("daily_hours", str(st.session_state.set_daily))
    set_setting("weekly_hours", str(st.session_state.set_weekly))
    set_setting("ignore_weekends", "1" if st.session_state.set_ignore_we else "0")
    set_setting("reminders_enabled", "1" if st.session_state.set_reminders else "0")
    set_setting("reminder_entry", st.session_state.set_rem_entry)
    set_setting("reminder_exit", st.session_state.set_rem_exit)
    st.session_state.settings_saved = True


def add_holiday_callback():
    """Called when 'Adicionar Feriado' is clicked."""
    name = st.session_state.holiday_name.strip()
    holiday_date = st.session_state.holiday_date
    recurring = st.session_state.holiday_recurring

    if not name:
        st.session_state.holiday_error = "Nome é obrigatório."
        return

    create_holiday(name, holiday_date, recurring)
    st.session_state.holiday_error = ""
    st.session_state.holiday_added = name
    st.session_state.holiday_name = ""
    st.session_state.holiday_date = date.today()
    st.session_state.holiday_recurring = False


# ═══════════════════════════════════════════════
# SECTION 1: Carga Horária
# ═══════════════════════════════════════════════

st.header("🕐 Carga Horária")

settings = get_all_settings()

# Init widget session keys
for key, default in [
    ("set_daily", 8.0),
    ("set_weekly", 40.0),
    ("set_ignore_we", True),
    ("set_reminders", False),
    ("set_rem_entry", "08:00"),
    ("set_rem_exit", "17:30"),
]:
    if key not in st.session_state:
        val = settings.get(key.replace("set_", "").replace("ignore_we", "ignore_weekends"), str(default))
        if isinstance(default, float):
            st.session_state[key] = float(val)
        elif isinstance(default, bool):
            st.session_state[key] = val in ("1", "True", True)
        else:
            st.session_state[key] = str(val)

st.number_input(
    "Carga horária diária (horas)",
    min_value=1.0, max_value=24.0, step=0.5,
    key="set_daily",
)
st.number_input(
    "Carga horária semanal (horas)",
    min_value=1.0, max_value=168.0, step=1.0,
    key="set_weekly",
)
st.checkbox(
    "Excluir fins de semana (Sáb/Dom) do cálculo de banco de horas",
    key="set_ignore_we",
    help="Quando ativado, sábado e domingo não contam como dias úteis.",
)

st.markdown("---")
st.subheader("🔔 Lembretes (experimental)")

st.checkbox(
    "Ativar notificações desktop",
    key="set_reminders",
    help="Exibe notificações do sistema para lembrar de bater ponto.",
)

col1, col2 = st.columns(2)
with col1:
    st.text_input("Horário lembrete de entrada", key="set_rem_entry", help="Formato HH:MM")
with col2:
    st.text_input("Horário lembrete de saída", key="set_rem_exit", help="Formato HH:MM")

if st.session_state.settings_saved:
    st.success("✅ Configurações salvas!")
    st.session_state.settings_saved = False

st.button("💾 Salvar Configurações", on_click=save_settings_callback, type="primary")

# Current settings table
current = get_all_settings()
st.markdown("---")
st.markdown(f"""
| Configuração | Valor |
|---|---|
| Carga horária diária | **{current.get('daily_hours', '8')}h** |
| Carga horária semanal | **{current.get('weekly_hours', '40')}h** |
| Ignorar fins de semana | **{'Sim' if current.get('ignore_weekends', '1') == '1' else 'Não'}** |
| Lembretes ativos | **{'Sim' if current.get('reminders_enabled', '0') == '1' else 'Não'}** |
""")


# ═══════════════════════════════════════════════
# SECTION 2: Feriados
# ═══════════════════════════════════════════════

st.markdown("---")
st.header("🎌 Feriados")
st.caption("Feriados são excluídos do cálculo de dias úteis no banco de horas.")

# Success message
if st.session_state.holiday_added:
    st.success(f"✅ Feriado '{st.session_state.holiday_added}' adicionado!")
    st.session_state.holiday_added = ""

# Init holiday widget keys
if "holiday_name" not in st.session_state:
    st.session_state.holiday_name = ""
if "holiday_date" not in st.session_state:
    st.session_state.holiday_date = date.today()
if "holiday_recurring" not in st.session_state:
    st.session_state.holiday_recurring = False
if "holiday_error" not in st.session_state:
    st.session_state.holiday_error = ""

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    st.text_input("Nome do Feriado", key="holiday_name", placeholder="Ex: Natal")
with col2:
    st.date_input("Data", key="holiday_date", format="DD/MM/YYYY")
with col3:
    st.checkbox("Anual", key="holiday_recurring", help="Repete todo ano")

if st.session_state.holiday_error:
    st.error(st.session_state.holiday_error)
    st.session_state.holiday_error = ""

st.button("➕ Adicionar Feriado", on_click=add_holiday_callback, type="primary")

# List holidays
holidays = get_holidays()
if holidays:
    df_h = pd.DataFrame([
        {
            "ID": h["id"],
            "Nome": h["name"],
            "Data": date.fromisoformat(h["date"]).strftime("%d/%m"),
            "Ano": date.fromisoformat(h["date"]).year,
            "Recorrente": "✅" if h["recurring"] else "❌",
        }
        for h in holidays
    ])
    st.dataframe(df_h, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.caption("Excluir feriado pelo ID:")
    del_id = st.number_input("ID do feriado", min_value=1, step=1, key="del_holiday")
    if st.button("🗑️ Excluir Feriado", key="del_holiday_btn"):
        delete_holiday(del_id)
        st.success("Feriado excluído!")
        st.rerun()
else:
    st.info("Nenhum feriado cadastrado. Adicione os feriados do seu calendário.")
