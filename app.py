import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
import bcrypt
from pathlib import Path

# -----------------------------
# CONFIGURAÇÃO E TEMA
# -----------------------------
st.set_page_config(page_title="Up Tecnologia - Enterprise", layout="wide", page_icon="🏢")

PRIMARY = "#0E4A67"      # azul petróleo
ACCENT = "#C9A227"       # dourado
BG_LIGHT = "#F7F9FC"

# Cabeçalho com logo
def header():
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        logo_path = Path("logo.png")
        if logo_path.exists():
            st.image(str(logo_path), use_column_width=True)
    with col_title:
        st.markdown(f"""
        <div style="padding:8px 16px; background:{BG_LIGHT}; border-radius:12px; border:1px solid #eaeaea;">
            <h2 style="margin:0; color:{PRIMARY};">Up Tecnologia Ltda</h2>
            <p style="margin:0; color:#555;">HelpDesk • Portal de Chamados</p>
        </div>
        """, unsafe_allow_html=True)

# -----------------------------
# BANCO DE DADOS
# -----------------------------
DB_NAME = 'up_tecnologia_v10.db'

def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS empresas 
                 (cnpj TEXT PRIMARY KEY, nome_empresa TEXT, cidade TEXT, gerente_geral TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                 (username TEXT PRIMARY KEY, senha_hash BLOB, cnpj TEXT, nome_completo TEXT, tipo TEXT,
                  FOREIGN KEY(cnpj) REFERENCES empresas(cnpj))''')
    c.execute('''CREATE TABLE IF NOT EXISTS chamados 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, cnpj TEXT, autor TEXT, problema TEXT, 
                  status TEXT, etapa TEXT, data_abertura TEXT, valor REAL,
                  FOREIGN KEY(cnpj) REFERENCES empresas(cnpj))''')
    # Admin padrão (hash seguro)
    admin_user = 'diogenestulio'
    admin_pass = 'DmC61ACB433@'
    c.execute("SELECT username FROM usuarios WHERE username=?", (admin_user,))
    if not c.fetchone():
        senha_hash = bcrypt.hashpw(admin_pass.encode(), bcrypt.gensalt())
        c.execute("INSERT INTO usuarios (username, senha_hash, cnpj, nome_completo, tipo) VALUES (?,?,?,?,?)",
                  (admin_user, senha_hash, '00.000.000/0001-00', 'Diógenes Túlio', 'admin'))
    conn.commit()
    conn.close()

init_db()

# -----------------------------
# FUNÇÕES DE DADOS (com caching)
# -----------------------------
@st.cache_data(ttl=60)
def list_empresas():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM empresas", conn)
    conn.close()
    return df

@st.cache_data(ttl=60)
def list_usuarios():
    conn = get_conn()
    df = pd.read_sql_query("SELECT username, cnpj, nome_completo, tipo FROM usuarios", conn)
    conn.close()
    return df

@st.cache_data(ttl=30)
def list_chamados():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM chamados ORDER BY id DESC", conn)
    conn.close()
    return df

def get_chamados_por_cnpj(cnpj):
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM chamados WHERE cnpj=? ORDER BY id DESC", conn, params=(cnpj,))
    conn.close()
    return df

def autenticar(username, senha):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT senha_hash, tipo, cnpj, nome_completo FROM usuarios WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    if row and bcrypt.checkpw(senha.encode(), row[0]):
        return {"tipo": row[1], "cnpj": row[2], "nome": row[3]}
    return None

# -----------------------------
# EDIÇÃO DE DADOS (persistência)
# -----------------------------
def editar_empresas(df_editado):
    conn = get_conn()
    c = conn.cursor()
    # Limpeza e re-inserção simples (para demo). Em produção, faça UPSERT por linha.
    c.execute("DELETE FROM empresas")
    for _, r in df_editado.iterrows():
        c.execute("INSERT INTO empresas (cnpj, nome_empresa, cidade, gerente_geral) VALUES (?,?,?,?)",
                  (r['cnpj'], r['nome_empresa'], r['cidade'], r['gerente_geral']))
    conn.commit()
    conn.close()
    st.success("Empresas atualizadas com sucesso!")
    list_empresas.clear()  # limpa cache

def editar_usuarios(df_editado):
    conn = get_conn()
    c = conn.cursor()
    # Mantém hash; não edite senha diretamente aqui.
    c.execute("DELETE FROM usuarios WHERE tipo!='admin'")  # preserva admin
    for _, r in df_editado.iterrows():
        # Para novos usuários, defina senha padrão e hash
        senha_hash = bcrypt.hashpw("SenhaInicial123!".encode(), bcrypt.gensalt())
        c.execute("""INSERT OR REPLACE INTO usuarios (username, senha_hash, cnpj, nome_completo, tipo)
                     VALUES (?,?,?,?,?)""",
                  (r['username'], senha_hash, r['cnpj'], r['nome_completo'], r['tipo']))
    conn.commit()
    conn.close()
    st.success("Usuários atualizados com sucesso!")
    list_usuarios.clear()

def editar_chamados(df_editado):
    conn = get_conn()
    c = conn.cursor()
    for _, r in df_editado.iterrows():
        c.execute("""UPDATE chamados SET cnpj=?, autor=?, problema=?, status=?, etapa=?, data_abertura=?, valor=?
                     WHERE id=?""",
                  (r['cnpj'], r['autor'], r['problema'], r['status'], r['etapa'], r['data_abertura'], r['valor'], r['id']))
    conn.commit()
    conn.close()
    st.success("Chamados atualizados com sucesso!")
    list_chamados.clear()

# -----------------------------
# UI: LOGIN
# -----------------------------
if 'auth' not in st.session_state:
    st.session_state['auth'] = None

if not st.session_state['auth']:
    header()
    st.title("🛡️ Acesso Restrito")
    with st.form("login"):
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        ok = st.form_submit_button("Entrar")
        if ok:
            res = autenticar(u, p)
            if res:
                st.session_state['auth'] = {"user": u, **res}
                st.toast(f"Bem-vindo, {res['nome']}!", icon="👋")
                st.rerun()
            else:
                st.error("Credenciais incorretas.")
    st.stop()

# -----------------------------
# UI: LAYOUT PRINCIPAL
# -----------------------------
header()
perfil = st.session_state['auth']['tipo']
cnpj_user = st.session_state['auth']['cnpj']
nome_user = st.session_state['auth']['nome']

st.sidebar.title("Navegação")
if perfil == 'admin':
    menu = st.sidebar.radio("Painel Gestor", ["Dashboard", "Chamados", "Empresas", "Usuários", "Relatórios"])
else:
    menu = st.sidebar.radio("Portal do Cliente", ["Abrir Chamado", "Meus Chamados"])

# -----------------------------
# ADMIN: DASHBOARD
# -----------------------------
if perfil == 'admin' and menu == "Dashboard":
    st.title("📊 Visão Geral")
    df_ch = list_chamados()
    df_emp = list_empresas()
    df_usr = list_usuarios()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Receita Total", f"R$ {df_ch['valor'].sum():.2f}")
    c2.metric("Chamados", len(df_ch))
    c3.metric("Clientes", len(df_emp))
    c4.metric("Usuários", len(df_usr))

    # Gráficos de status
    colA, colB = st.columns(2)
    with colA:
        fig1 = px.bar(df_ch.groupby('status')['id'].count().reset_index(),
                      x='status', y='id', title='Chamados por Status',
                      color='status', color_discrete_sequence=[PRIMARY, ACCENT])
        st.plotly_chart(fig1, use_container_width=True)
    with colB:
        fig2 = px.pie(df_ch, names='etapa', title='Distribuição por Etapa',
                      color_discrete_sequence=px.colors.sequential.Blues)
        st.plotly_chart(fig2, use_container_width=True)

# -----------------------------
# ADMIN: CHAMADOS (listar/editar)
# -----------------------------
if perfil == 'admin' and menu == "Chamados":
    st.title("🛠️ Gestão de Chamados")
    df_ch = list_chamados()

    # Filtros
    colf1, colf2, colf3 = st.columns(3)
    with colf1:
        f_status = st.selectbox("Filtrar por Status", ["Todos"] + sorted(df_ch['status'].unique().tolist()))
    with colf2:
        f_etapa = st.selectbox("Filtrar por Etapa", ["Todos"] + sorted(df_ch['etapa'].unique().tolist()))
    with colf3:
        f_cnpj = st.selectbox("Filtrar por CNPJ", ["Todos"] + sorted(df_ch['cnpj'].unique().tolist()))

    df_view = df_ch.copy()
    if f_status != "Todos":
        df_view = df_view[df_view['status'] == f_status]
    if f_etapa != "Todos":
        df_view = df_view[df_view['etapa'] == f_etapa]
    if f_cnpj != "Todos":
        df_view = df_view[df_view['cnpj'] == f_cnpj]

    st.subheader("Editar Chamados")
    edited = st.data_editor(
        df_view,
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "id": st.column_config.NumberColumn("ID", disabled=True),
            "valor": st.column_config.NumberColumn("Valor (R$)", step=50.0),
            "data_abertura": st.column_config.TextColumn("Data Abertura (dd/mm HH:MM)")
        }
    )
    if st.button("Salvar alterações de chamados"):
        editar_chamados(edited)

# -----------------------------
# ADMIN: EMPRESAS (listar/editar)
# -----------------------------
if perfil == 'admin' and menu == "Empresas":
    st.title("🏢 Empresas Cadastradas")
    df_emp = list_empresas()

    st.subheader("Editar Empresas")
    edited_emp = st.data_editor(
        df_emp,
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "cnpj": st.column_config.TextColumn("CNPJ"),
            "nome_empresa": st.column_config.TextColumn("Nome Fantasia"),
            "cidade": st.column_config.TextColumn("Cidade"),
            "gerente_geral": st.column_config.TextColumn("Gerente")
        }
    )
    if st.button("Salvar alterações de empresas"):
        editar_empresas(edited_emp)

# -----------------------------
# ADMIN: USUÁRIOS (listar/editar)
# -----------------------------
if perfil == 'admin' and menu == "Usuários":
    st.title("👥 Usuários")
    df_usr = list_usuarios()

    st.subheader("Editar Usuários (exceto admin)")
    edited_usr = st.data_editor(
        df_usr[df_usr['tipo'] != 'admin'],
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "username": st.column_config.TextColumn("Login"),
            "cnpj": st.column_config.TextColumn("CNPJ"),
            "nome_completo": st.column_config.TextColumn("Nome Completo"),
            "tipo": st.column_config.SelectboxColumn("Tipo", options=["cliente", "admin"])
        }
    )
    if st.button("Salvar alterações de usuários"):
        editar_usuarios(edited_usr)

# -----------------------------
# ADMIN: RELATÓRIOS
# -----------------------------
if perfil == 'admin' and menu == "Relatórios":
    st.title("📈 Relatórios")
    df_ch = list_chamados()
    col1, col2 = st.columns(2)
    with col1:
        finalizados = df_ch[df_ch['status'] == 'Finalizado']
        pendentes = df_ch[df_ch['status'] != 'Finalizado']
        st.metric("Finalizados", len(finalizados))
        st.metric("Pendentes", len(pendentes))
    with col2:
        fig = px.line(df_ch, x='id', y='valor', color='status', title='Valores por Chamado')
        st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# CLIENTE: ABRIR CHAMADO
# -----------------------------
if perfil != 'admin' and menu == "Abrir Chamado":
    st.title("➕ Abrir Chamado")
    with st.form("novo_ch"):
        desc = st.text_area("Descreva o problema ou solicitação técnica")
        enviar = st.form_submit_button("Enviar para Up Tecnologia")
        if enviar and desc.strip():
            conn = get_conn()
            conn.execute("""INSERT INTO chamados (cnpj, autor, problema, status, etapa, data_abertura, valor)
                            VALUES (?,?,?,?,?,?,?)""",
                         (cnpj_user, nome_user, desc.strip(), "Aberto", "Pendente",
                          datetime.now().strftime("%d/%m %H:%M"), 0.0))
            conn.commit()
            conn.close()
            st.success("Chamado enviado! Equipe será notificada.")
            list_chamados.clear()
        elif enviar:
            st.error("Por favor, descreva o problema.")

# -----------------------------
# CLIENTE: MEUS CHAMADOS
# -----------------------------
if perfil != 'admin' and menu == "Meus Chamados":
    st.title("📋 Meus Chamados")
    df_cli = get_chamados_por_cnpj(cnpj_user)
    st.dataframe(df_cli[['data_abertura', 'autor', 'problema', 'etapa', 'status', 'valor']], use_container_width=True)

# -----------------------------
# SAIR
# -----------------------------
if st.sidebar.button("Sair"):
    st.session_state['auth'] = None
    st.rerun()