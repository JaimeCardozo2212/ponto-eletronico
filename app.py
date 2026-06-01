"""
Sistema de Apontamento de Horas — Entry Point.
Run with: streamlit run app.py
"""

import streamlit as st
from database import init_db

# ── Page config MUST be the first Streamlit call ──
st.set_page_config(
    page_title="Ponto Eletrônico",
    page_icon="⏱️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──
st.markdown("""
<style>
    /* Cards */
    .metric-card {
        background: linear-gradient(135deg, #1f1f2e 0%, #2d2d44 100%);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        border: 1px solid rgba(255,255,255,0.08);
        text-align: center;
    }
    .metric-card .label {
        font-size: 0.85rem;
        color: #a0a0b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.4rem;
    }
    .metric-card .value {
        font-size: 2rem;
        font-weight: 700;
        color: #ffffff;
    }
    .metric-card .value.positive { color: #4ade80; }
    .metric-card .value.negative { color: #f87171; }

    /* Alert boxes */
    .alert-box {
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
        font-weight: 500;
    }
    .alert-warning {
        background: rgba(251, 191, 36, 0.15);
        border: 1px solid rgba(251, 191, 36, 0.4);
        color: #fbbf24;
    }
    .alert-info {
        background: rgba(96, 165, 250, 0.12);
        border: 1px solid rgba(96, 165, 250, 0.3);
        color: #93c5fd;
    }

    /* Divider */
    .section-divider {
        margin: 1.5rem 0;
        border-top: 1px solid rgba(255,255,255,0.08);
    }
</style>
""", unsafe_allow_html=True)

# ── Initialize database ──
init_db()

# ── Sidebar Navigation ──
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/time-span.png", width=64)
    st.title("Ponto Eletrônico")
    st.caption("Controle de horas & projetos")

    st.markdown("---")
    page = st.radio(
        "Navegação",
        [
            "🏠 Registrar Ponto",
            "📋 Projetos",
            "📊 Dashboard",
            "📅 Histórico",
            "⚙️ Configurações",
            "📥 Exportar Excel",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.caption("💡 Dica: use o Dashboard para análises visuais")
    st.caption(f"📁 Banco de dados: `data/ponto.db`")

# ── Route to pages ──
page_map = {
    "🏠 Registrar Ponto": "pages/1_registro.py",
    "📋 Projetos": "pages/2_projetos.py",
    "📊 Dashboard": "pages/3_dashboard.py",
    "📅 Histórico": "pages/4_historico.py",
    "⚙️ Configurações": "pages/5_configuracoes.py",
    "📥 Exportar Excel": "pages/6_exportar.py",
}

page_file = page_map.get(page)
if page_file:
    with open(page_file, encoding="utf-8") as f:
        code = compile(f.read(), page_file, "exec")
        exec(code, {"__name__": "__main__"})
