import streamlit as st
import pandas as pd
import sqlite3
import smtplib
import plotly.express as px
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Up Tecnologia - Gestão Pro", layout="wide", page_icon="🚀")

DB_NAME = 'up_tecnologia_v4.db'

# --- DESIGN CSS ---
st.markdown("""
    <style>
    .stMetric { border: 1px solid #e0e0e0; padding: 15px; border-radius: 10px; background: #ffffff; }
    .stButton>button { border-radius: 5px; height: 3em; background-color: #004a99; color: white; }
    .sidebar .sidebar-content { background-image: linear-gradient(#2e7bcf,#2e7bcf); color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- BASE DE DADOS ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                 (username TEXT PRIMARY KEY, senha TEXT, cnpj TEXT, 
                  nome_empresa TEXT, cidade TEXT, gerente TEXT, tipo TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS chamados 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, cnpj TEXT, cliente TEXT, problema TEXT, 
                  status TEXT, data_abertura TEXT, data_fim TEXT, valor REAL)''')
    c.execute("INSERT OR IGNORE INTO usuarios VALUES (?,?,?,?,?,?,?)", 
              ('diogenestulio', 'DmC61ACB433@', '00.000.000/0001-00', 'Up Tecnologia', 'Sede', 'Diógenes', 'admin'))
    conn.commit()
    conn.close()

init_db()

# --- FUNÇÕES DE SUPORTE (PDF E E-MAIL) ---
def gerar_pdf_mensal(df, mes_ano):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "UP TECNOLOGIA - RELATORIO MENSAL", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 10)
    total = df['valor'].sum()
    pdf.cell(200, 10, f"Total de Chamados: {len(df)} | Faturamento: R$ {total:.2f}", ln=True)
    pdf.ln(5)
    for i, r in df.iterrows():
        pdf.cell(190, 10, f"{r['data_abertura']} - {r['cnpj']} - R$ {r['valor']:.2f}", 1, ln=True)
    return pdf.output(dest='S').encode('latin-1')

def enviar_backup_email():
    try:
        e_user = st.secrets["EMAIL_USER"]
        e_pass = st.secrets["EMAIL_PASS"]
        e_dest = st.secrets["EMAIL_DESTINO"]
        msg = MIMEMultipart()
        msg['Subject'] = f"Backup Up Tecnologia - {datetime.now().strftime('%d/%m/%Y')}"
        with open(DB_NAME, "rb") as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read()); encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename={DB_NAME}")
            msg.attach(part)
        s = smtplib.SMTP('smtp.gmail.com', 587); s.starttls(); s.login(e_user, e_pass)
        s.sendmail(e_user, e_dest, msg.as_string()); s.quit()
        return True
    except: return False

# --- LOGICA DE LOGIN ---
if 'logado' not in st.session_state: st.session_state['logado'] = False

if not st.session_state['logado']:
    st.title("🚀 Up Tecnologia LTDA")
    with st.container():
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT tipo, cnpj, nome_empresa FROM usuarios WHERE username=? AND senha=?", (u, p))
            res = c.fetchone()
            if res:
                st.session_state.update({'logado':True, 'user':u, 'tipo':res[0], 'cnpj':res[1], 'empresa':res[2]})
                st.rerun()
            else: st.error("Acesso Negado")
else:
    # --- ÁREA ADMINISTRADOR ---
    if st.session_state['tipo'] == 'admin':
        conn = sqlite3.connect(DB_NAME)
        df_all = pd.read_sql_query("SELECT * FROM chamados", conn)
        chamados_abertos = len(df_all[df_all['status'] == 'Aberto'])
        
        # NOTIFICAÇÃO TOAST
        if chamados_abertos > 0:
            st.toast(f"Atenção: Existem {chamados_abertos} chamados pendentes!", icon="⚠️")

        st.sidebar.title("🛠️ Administração")
        menu = st.sidebar.radio("Navegação", [
            "Métricas", 
            f"Suporte ({chamados_abertos})", 
            "Clientes", 
            "Segurança"
        ])

        if menu == "Métricas":
            st.title("📊 Dashboard Financeiro")
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Chamados", len(df_all))
            c2.metric("Pendentes", chamados_abertos)
            c3.metric("Receita Total", f"R$ {df_all['valor'].sum():.2f}")
            
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                fig_bar = px.bar(df_all.groupby('cnpj')['valor'].sum().reset_index(), x='cnpj', y='valor', title="Receita por Cliente", color='valor')
                st.plotly_chart(fig_bar, use_container_width=True)
            with col_g2:
                fig_pie = px.pie(df_all, names='status', title="Status dos Chamados")
                st.plotly_chart(fig_pie, use_container_width=True)

        elif "Suporte" in menu:
            st.title("✅ Gestão de Chamados")
            df_pend = df_all[df_all['status'] == 'Aberto']
            if not df_pend.empty:
                id_sel = st.selectbox("Selecione o Chamado para Finalizar", df_pend['id'])
                valor_servico = st.number_input("Valor do Serviço (R$)", min_value=0.0)
                if st.button("Finalizar e Cobrar"):
                    c = conn.cursor()
                    c.execute("UPDATE chamados SET status='Finalizado', data_fim=?, valor=? WHERE id=?", 
                              (datetime.now().strftime("%d/%m/%Y %H:%M"), valor_servico, id_sel))
                    conn.commit()
                    st.success("Chamado fechado com sucesso!")
                    st.rerun()
            else: st.info("Não há chamados abertos no momento.")
            st.divider()
            st.dataframe(df_all, use_container_width=True)

        elif menu == "Clientes":
            st.title("👥 Cadastro de Unidades")
            with st.form("cad_cli"):
                c1, c2 = st.columns(2)
                with c1:
                    un = st.text_input("Username"); ps = st.text_input("Senha")
                    cj = st.text_input("CNPJ")
                with c2:
                    ne = st.text_input("Nome Empresa"); ci = st.text_input("Cidade")
                    ge = st.text_input("Gerente")
                if st.form_submit_button("Cadastrar"):
                    c = conn.cursor()
                    c.execute("INSERT INTO usuarios VALUES (?,?,?,?,?,?,?)", (un, ps, cj, ne, ci, ge, 'cliente'))
                    conn.commit(); st.success("Cliente Cadastrado!")

        elif menu == "Segurança":
            st.title("🛡️ Backups")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🚀 Backup por E-mail"):
                    if enviar_backup_email(): st.success("Enviado!")
                    else: st.error("Falha no SMTP.")
            with col_b:
                pdf_data = gerar_pdf_mensal(df_all, "Mensal")
                st.download_button("📥 Baixar PDF Financeiro", pdf_data, "relatorio.pdf")

    # --- ÁREA CLIENTE ---
    else:
        st.title(f"Portal Up Tecnologia - {st.session_state['empresa']}")
        with st.form("cli_chamado"):
            p = st.text_area("Descreva o seu problema:")
            if st.form_submit_button("Abrir Chamado"):
                c = conn.cursor()
                c.execute("INSERT INTO chamados (cnpj, cliente, problema, status, data_abertura, valor) VALUES (?,?,?,?,?,?)",
                          (st.session_state['cnpj'], st.session_state['user'], p, "Aberto", datetime.now().strftime("%d/%m/%Y %H:%M"), 0.0))
                conn.commit(); st.success("Recebemos a sua solicitação!")

    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()
