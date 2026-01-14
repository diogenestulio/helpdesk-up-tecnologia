import streamlit as st
import sqlite3
import plotly.express as px
from datetime import datetime
import re
from pathlib import Path

# --- CONFIGURAÇÃO ---
DB_NAME = "up_tecnologia_final.db"
conn = sqlite3.connect(DB_NAME)

# Paleta de cores
PRIMARY = "#0E4A67"   # Azul petróleo
ACCENT = "#C9A227"    # Dourado
BG_LIGHT = "#F7F9FC"  # Fundo claro

# --- BANCO DE DADOS ---
def init_db():
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS empresas 
                 (cnpj TEXT PRIMARY KEY, nome_empresa TEXT, cidade TEXT, gerente_geral TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                 (username TEXT PRIMARY KEY, senha TEXT, cnpj TEXT, nome_completo TEXT, tipo TEXT,
                  FOREIGN KEY(cnpj) REFERENCES empresas(cnpj))''')
    c.execute('''CREATE TABLE IF NOT EXISTS chamados 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, cnpj TEXT, autor TEXT, problema TEXT, 
                  status TEXT, etapa TEXT, data_abertura TEXT, valor REAL)''')
    conn.commit()

init_db()

# --- FUNÇÕES DE CNPJ ---
def formatar_cnpj(cnpj: str) -> str:
    numeros = re.sub(r"\D", "", cnpj)
    if len(numeros) > 14:
        numeros = numeros[:14]
    formato = ""
    if len(numeros) >= 2:
        formato += numeros[:2] + "."
    if len(numeros) >= 5:
        formato += numeros[2:5] + "."
    if len(numeros) >= 8:
        formato += numeros[5:8] + "/"
    if len(numeros) >= 12:
        formato += numeros[8:12] + "-"
    if len(numeros) > 12:
        formato += numeros[12:]
    return formato

def validar_cnpj(cnpj: str) -> bool:
    padrao = r"^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$"
    return re.match(padrao, cnpj) is not None

# --- CABEÇALHO COM LOGO ---
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
            <p style="margin:0; color:{ACCENT};">HelpDesk • Portal de Chamados</p>
        </div>
        """, unsafe_allow_html=True)

# --- INTERFACE ---
st.set_page_config(page_title="Up Tecnologia - HelpDesk", layout="wide", page_icon="🏢")
header()

menu = st.sidebar.radio("Navegação", ["Cadastro Empresa/Responsável", "Gestão de Chamados", "Dashboard"])

# --- CADASTRO SIMPLIFICADO ---
if menu == "Cadastro Empresa/Responsável":
    st.header("🚀 Cadastro Rápido - Empresa + Responsável")

    with st.form("cadastro_completo"):
        st.subheader("🏢 Dados da Empresa")
        cnpj_input = st.text_input("CNPJ da Empresa (digite apenas números)", help="Será formatado automaticamente")
        cnpj = formatar_cnpj(cnpj_input)
        st.write(f"📌 CNPJ formatado: **{cnpj}**")

        nome = st.text_input("Nome Fantasia")
        cidade = st.text_input("Cidade")
        gerente = st.text_input("Gerente da Unidade")

        st.subheader("👤 Dados do Responsável")
        usuario = st.text_input("Login (Username)")
        senha = st.text_input("Senha Inicial", type="password")
        nome_resp = st.text_input("Nome Completo do Responsável")

        st.subheader("🔎 Pré-visualização")
        st.write(f"**Empresa:** {nome} | **CNPJ:** {cnpj} | **Cidade:** {cidade} | **Gerente:** {gerente}")
        st.write(f"**Responsável:** {nome_resp} | **Usuário:** {usuario}")

        finalizar = st.form_submit_button("✅ Finalizar Cadastro")

        if finalizar:
            if not validar_cnpj(cnpj):
                st.error("⚠️ CNPJ inválido! Use o formato 00.000.000/0001-00.")
            elif cnpj and nome and usuario and senha and nome_resp:
                try:
                    conn.execute("INSERT INTO empresas VALUES (?,?,?,?)", (cnpj, nome, cidade, gerente))
                    conn.execute("INSERT INTO usuarios VALUES (?,?,?,?,?)", (usuario, senha, cnpj, nome_resp, 'cliente'))
                    conn.commit()
                    st.success("🎉 Empresa e responsável cadastrados com sucesso!")
                    st.balloons()
                except sqlite3.IntegrityError:
                    st.error("⚠️ Já existe uma empresa ou usuário com esses dados.")
            else:
                st.error("⚠️ Preencha todos os campos obrigatórios.")

    st.divider()
    st.subheader("📋 Empresas cadastradas")
    empresas = conn.execute("SELECT * FROM empresas").fetchall()
    df_emp = st.data_editor(empresas, num_rows="dynamic", use_container_width=True,
                            column_config={0:"CNPJ",1:"Nome Fantasia",2:"Cidade",3:"Gerente"})
    if st.button("💾 Salvar alterações de empresas"):
        conn.execute("DELETE FROM empresas")
        for row in df_emp:
            conn.execute("INSERT INTO empresas VALUES (?,?,?,?)", tuple(row))
        conn.commit()
        st.success("✅ Empresas atualizadas!")

    st.subheader("👥 Usuários cadastrados")
    usuarios = conn.execute("SELECT username, nome_completo, cnpj, tipo FROM usuarios").fetchall()
    df_usr = st.data_editor(usuarios, num_rows="dynamic", use_container_width=True,
                            column_config={0:"Login",1:"Nome Completo",2:"CNPJ",3:"Tipo"})
    if st.button("💾 Salvar alterações de usuários"):
        conn.execute("DELETE FROM usuarios WHERE tipo!='admin'")
        for row in df_usr:
            conn.execute("INSERT OR REPLACE INTO usuarios (username, senha, cnpj, nome_completo, tipo) VALUES (?,?,?,?,?)",
                         (row[0], "SenhaInicial123!", row[2], row[1], row[3]))
        conn.commit()
        st.success("✅ Usuários atualizados!")

# --- GESTÃO DE CHAMADOS ---
elif menu == "Gestão de Chamados":
    st.header("🛠️ Gestão de Chamados")
    chamados = conn.execute("SELECT * FROM chamados").fetchall()
    df_ch = st.data_editor(chamados, num_rows="dynamic", use_container_width=True,
                           column_config={0:"ID",1:"CNPJ",2:"Autor",3:"Problema",4:"Status",
                                          5:"Etapa",6:"Data Abertura",7:"Valor"})
    if st.button("💾 Salvar alterações de chamados"):
        for row in df_ch:
            conn.execute("""UPDATE chamados SET cnpj=?, autor=?, problema=?, status=?, etapa=?, data_abertura=?, valor=? WHERE id=?""",
                         (row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[0]))
        conn.commit()
        st.success("✅ Chamados atualizados!")

# --- DASHBOARD ---
elif menu == "Dashboard":
    st.header("📊 Visão Geral")
    df_ch = conn.execute("SELECT * FROM chamados").fetchall()
    df_emp = conn.execute("SELECT * FROM empresas").fetchall()
    df_usr = conn.execute("SELECT * FROM usuarios").fetchall()

    col1, col2, col3 = st.columns(3)
    col1.metric("Chamados", len(df_ch))
    col2.metric("Empresas", len(df_emp))
    col3.metric("Usuários", len(df_usr))

    if df_ch:
        import pandas as pd
        df_ch = pd.DataFrame(df_ch, columns=["ID","CNPJ","Autor","Problema","Status","Etapa","Data","Valor"])
        fig1 = px.bar(df_ch.groupby("Status")["ID"].count().reset_index(),
                      x="Status", y="ID", title="Chamados por Status",
                      color="Status", color_discrete_sequence=[PRIMARY, ACCENT])
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.pie(df_ch, names="Etapa", title="Distribuição por Etapa",
                      color_discrete_sequence