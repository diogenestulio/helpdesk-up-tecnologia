import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime
import re
from pathlib import Path

# -----------------------------
# CONFIGURAÇÃO
# -----------------------------
st.set_page_config(page_title="Up Tecnologia • HelpDesk Futurista", layout="wide", page_icon="💡")

DB_NAME = "helpdesk_futurista.db"

PRIMARY = "#0E4A67"   # Azul petróleo
ACCENT = "#C9A227"    # Dourado
BG_LIGHT = "#F7F9FC"  # Fundo claro
GLASS = "rgba(255,255,255,0.65)"  # Transparência estilo glassmorphism

# -----------------------------
# BANCO DE DADOS
# -----------------------------
def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS empresas 
                 (cnpj TEXT PRIMARY KEY, nome_empresa TEXT, cidade TEXT, gerente_geral TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                 (username TEXT PRIMARY KEY, senha TEXT, cnpj TEXT, nome_completo TEXT, tipo TEXT,
                  FOREIGN KEY(cnpj) REFERENCES empresas(cnpj))''')
    c.execute('''CREATE TABLE IF NOT EXISTS chamados 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, cnpj TEXT, autor TEXT, problema TEXT, 
                  status TEXT, etapa TEXT, data_abertura TEXT, valor REAL,
                  FOREIGN KEY(cnpj) REFERENCES empresas(cnpj))''')
    conn.commit()
    conn.close()

init_db()

# -----------------------------
# UTILITÁRIOS
# -----------------------------
def formatar_cnpj(cnpj: str) -> str:
    numeros = re.sub(r"\D", "", cnpj)
    if len(numeros) > 14: numeros = numeros[:14]
    if len(numeros) < 14: return numeros
    return f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:]}"

def validar_cnpj(cnpj: str) -> bool:
    padrao = r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$"
    return re.match(padrao, cnpj) is not None

def header():
    col_logo, col_title, col_user = st.columns([1, 4, 2])
    with col_logo:
        logo_path = Path("logo.png")
        if logo_path.exists():
            st.image(str(logo_path), use_column_width=True)
    with col_title:
        st.markdown(f"""
        <div style="padding:16px; backdrop-filter: blur(8px); background:{GLASS}; border-radius:16px; border:1px solid #eaeaea;">
            <h2 style="margin:0; color:{PRIMARY};">Up Tecnologia Ltda</h2>
            <p style="margin:0; color:{ACCENT};">HelpDesk • Portal Futurista</p>
        </div>
        """, unsafe_allow_html=True)
    with col_user:
        if st.session_state.get("auth"):
            st.markdown(f"""
            <div style="padding:12px; background:{BG_LIGHT}; border-radius:12px; border:1px solid #eaeaea;">
                <strong>Usuário:</strong> {st.session_state['auth']['nome']}<br>
                <strong>Perfil:</strong> {st.session_state['auth']['tipo']}<br>
                <strong>CNPJ:</strong> {st.session_state['auth']['cnpj']}
            </div>
            """, unsafe_allow_html=True)

# -----------------------------
# LOGIN / PRIMEIRO ACESSO
# -----------------------------
if "auth" not in st.session_state:
    st.session_state["auth"] = None

# Verifica se já existe administrador
conn = get_conn()
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM usuarios WHERE tipo='admin'")
tem_admin = c.fetchone()[0]
conn.close()

# Fluxo de primeiro acesso
if tem_admin == 0 and not st.session_state["auth"]:
    st.title("👑 Primeiro acesso - Criar Administrador")
    with st.form("primeiro_admin"):
        usuario = st.text_input("Usuário (login)")
        senha = st.text_input("Senha", type="password")
        nome = st.text_input("Nome completo")
        cnpj = st.text_input("CNPJ (opcional)")
        criar = st.form_submit_button("✅ Criar Administrador")
        if criar and usuario and senha and nome:
            conn = get_conn()
            conn.execute("INSERT INTO usuarios VALUES (?,?,?,?,?)",
                         (usuario, senha, cnpj if cnpj else "00.000.000/0001-00", nome, "admin"))
            conn.commit()
            conn.close()
            st.success("🎉 Administrador criado com sucesso! Você já está logado.")
            st.session_state["auth"] = {"user": usuario, "tipo": "admin", "cnpj": cnpj, "nome": nome}
            st.experimental_rerun()
    st.stop()

# Fluxo normal de login
if not st.session_state["auth"]:
    st.title("🔐 Login • Acesso ao HelpDesk")
    u = st.text_input("Usuário")
    p = st.text_input("Senha", type="password")
    if st.button("Entrar", type="primary"):
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT tipo, cnpj, nome_completo FROM usuarios WHERE username=? AND senha=?", (u, p))
        res = c.fetchone()
        conn.close()
        if res:
            st.session_state["auth"] = {"user": u, "tipo": res[0], "cnpj": res[1], "nome": res[2]}
            st.experimental_rerun()
        else:
            st.error("Credenciais incorretas.")
    st.stop()

# -----------------------------
# LAYOUT PRINCIPAL
# -----------------------------
header()
st.sidebar.success(f"Logado como: {st.session_state['auth']['nome']} ({st.session_state['auth']['tipo']})")
if st.sidebar.button("🚪 Sair"):
    st.session_state["auth"] = None
    st.experimental_rerun()

perfil = st.session_state["auth"]["tipo"]
cnpj_user = st.session_state["auth"]["cnpj"]
menu = st.sidebar.radio("Navegação", ["Abrir Chamado", "Kanban de Chamados", "Cadastro Empresa/Responsável", "Financeiro", "Dashboard"])

# -----------------------------
# ABRIR CHAMADO
# -----------------------------
if menu == "Abrir Chamado":
    st.subheader("➕ Abrir Chamado")
    with st.form("novo_ch"):
        desc = st.text_area("Descreva o problema ou solicitação técnica")
        enviar = st.form_submit_button("Enviar", type="primary")
        if enviar and desc.strip():
            conn = get_conn()
            conn.execute("""INSERT INTO chamados (cnpj, autor, problema, status, etapa, data_abertura, valor)
                            VALUES (?,?,?,?,?,?,?)""",
                         (cnpj_user, st.session_state["auth"]["nome"], desc.strip(),
                          "Aberto", "Pendente", datetime.now().strftime("%d/%m/%Y %H:%M"), 0.0))
            conn.commit()
            conn.close()
            st.success("Chamado enviado! Você pode acompanhar no Kanban.")
            st.balloons()

# -----------------------------
# KANBAN DE CHAMADOS
# -----------------------------
elif menu == "Kanban de Chamados":
    st.subheader("📌 Kanban de Chamados")
    conn = get_conn()
    if perfil == "admin":
        df = pd.read_sql_query("SELECT * FROM chamados ORDER BY id DESC", conn)
    else:
        df = pd.read_sql_query("SELECT * FROM chamados WHERE cnpj=? ORDER BY id DESC", conn, params=(cnpj_user,))
    conn.close()

    colA, colB, colC = st.columns(3)
    for col, status in zip([colA, colB, colC], ["Aberto", "Em Andamento", "Finalizado"]):
        with col:
            st.markdown(f"### {status}")
            subset = df[df["status"] == status]
            if subset.empty:
                st.caption("Sem chamados aqui.")
            for _, r in subset.iterrows():
                st.markdown(
                    f"""
                    <div style="margin-bottom:12px; padding:12px; backdrop-filter: blur(6px); 
                                background:{GLASS}; border-radius:12px; border:1px solid #eaeaea;">
                        <strong>#{int(r['id'])}</strong> • {r['problema']}<br>
                        <small>
                            Etapa: {r['etapa']} • Autor: {r['autor']} • 
                            Abertura: {r['data_abertura']} • Valor: R$ {r['valor']:.2f}
                        </small>
                    </div>
                    """,
                    unsafe_allow_html=True
            )
