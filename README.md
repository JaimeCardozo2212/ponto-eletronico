# ⏱️ Ponto Eletrônico

Sistema de apontamento de horas desenvolvido com **Streamlit** para controle de jornada diária, alocação de horas por projeto, dashboards analíticos e exportação de relatórios.

---

## 📸 Funcionalidades

| Página | Descrição |
|---|---|
| 🏠 **Registrar Ponto** | Registo diário com horário de entrada, almoço e saída. Alocação de horas por projeto com validação. |
| 📋 **Projetos** | CRUD de projetos com nome, descrição, cor e estado (ativo/inativo). |
| 📊 **Dashboard** | Visão geral com cards de horas trabalhadas, saldo, resumo semanal/mensal e gráficos interativos com Plotly. |
| 📅 **Histórico** | Listagem paginada de todos os registos com filtros por data e projeto. |
| ⚙️ **Configurações** | Definição de carga horária diária/semanal, feriados (fixos e recorrentes), ignorar fins de semana. |
| 📥 **Exportar Excel** | Exportação formatada em XLSX com 3 folhas: registos, alocações por projeto e resumo. |

---

## 🛠️ Stack

- **[Streamlit](https://streamlit.io/)** — Interface web
- **[SQLite](https://sqlite.org/)** — Base de dados local (`data/ponto.db`)
- **[Pandas](https://pandas.pydata.org/)** — Manipulação de dados
- **[Plotly](https://plotly.com/)** — Gráficos interativos
- **[OpenPyXL](https://openpyxl.readthedocs.io/)** — Geração de ficheiros Excel

---

## 🗄️ Estrutura da Base de Dados

```
time_entries        — registos diários (data, entrada, almoço, saída, notas)
projects            — projetos (nome, descrição, cor, ativo)
project_allocations — horas alocadas a projetos por registo
holidays            — feriados (fixos e recorrentes)
settings            — configurações (horas diárias, semanais, etc.)
```

---

## 🚀 Como Executar

```bash
# 1. Clona o repositório
git clone https://github.com/JaimeCardozo2212/ponto-eletronico.git
cd ponto-eletronico

# 2. Cria e ativa um ambiente virtual (opcional mas recomendado)
python -m venv venv
source venv/Scripts/activate   # Windows (bash)
# ou
venv\Scripts\activate          # Windows (cmd)

# 3. Instala as dependências
pip install -r requirements.txt

# 4. Executa a aplicação
streamlit run app.py
```

A aplicação abre automaticamente em `http://localhost:8501`.

---

## ⚙️ Configurações Padrão

| Configuração | Valor padrão |
|---|---|
| Carga horária diária | 8 horas |
| Carga horária semanal | 40 horas |
| Ignorar fins de semana | Sim |
| Lembrete de entrada | 08:00 |
| Lembrete de saída | 17:30 |

Estes valores podem ser alterados na página **⚙️ Configurações**.

---

## 📁 Estrutura do Projeto

```
ponto-eletronico/
├── app.py                  # Entry point — configuração Streamlit e navegação
├── database.py             # Schema SQLite, ligação e operações CRUD
├── utils.py                # Cálculo de horas, dias úteis, formatação
├── requirements.txt        # Dependências Python
├── pages/
│   ├── 1_registro.py       # Registo diário de ponto
│   ├── 2_projetos.py       # Gestão de projetos
│   ├── 3_dashboard.py      # Dashboard analítico
│   ├── 4_historico.py      # Histórico de registos
│   ├── 5_configuracoes.py  # Configurações e feriados
│   └── 6_exportar.py       # Exportação para Excel
└── data/
    └── ponto.db            # Base de dados SQLite (gerada automaticamente)
```

---

## 📄 Licença

Este projeto é para uso pessoal. Sem licença definida.
