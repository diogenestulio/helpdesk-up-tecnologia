import streamlit as st
import pandas as pd
import sqlite3
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from fpdf import FPDF

# --- CONFIGURAÇÃO DA PÁGINA E ESTILO ---
st.set_page_config(page_title="Up Tecnologia - Help Desk", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0px 2px 10px rgba(0,0,0,0.05); }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    </style>
    """, unsafe_all_boxes=True)

DB_NAME = 'up_tecnologia.db'

# --- FUNÇÕES DE BASE DE DADOS ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS usuarios (username TEXT PRIMARY KEY, senha TEXT, cnpj TEXT, tipo TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS chamados 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, cnpj TEXT, cliente TEXT, problema TEXT, 
                  status TEXT, data_abertura TEXT, data_fim TEXT, valor REAL)''')
    # Admin padrão (Recomendado usar Secrets aqui também no futuro)
    c.execute("INSERT OR IGNORE INTO usuarios VALUES (?, ?, ?, ?)", 
              ('diogenestulio', 'DmC61ACB433@', '00.000.000/0001-00', 'admin'))
    conn.commit()
    conn.close()

init_db()

# --- FUNÇÃO DE BACKUP POR E-MAIL (USANDO SECRETS) ---
def enviar_backup_email():
    try:
        # Puxa os dados do cofre do Streamlit
        email_origem = st.secrets["EMAIL_USER"]
        senha_app = st.secrets["EMAIL_PASS"]
        email_destino = st.secrets["EMAIL_DESTINO"]

        msg = MIMEMultipart()
        msg['From'] = email_origem
        msg['To'] = email_destino
        msg['Subject'] = f"🚀 BACKUP UP TECNOLOGIA - {datetime.now().strftime('%d/%m/%Y')}"

        with open(DB_NAME, "rb") as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename={DB_NAME}")
            msg.attach(part)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_origem, senha_app)
        server.sendmail(email_origem, email_destino, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        st.error(f"Erro no SMTP: {e}")
        return False

# --- LÓGICA DE INTERFACE ---
if 'logado' not in st.session_state:
    st.session_state['logado'] = False

if not st.session_state['logado']:
    st.sidebar.title("🚀 Up Tecnologia")
    st.subheader("🔑 Login do Sistema")
    u = st.text_input("Usuário")
    p = st.text_input("Senha", type="password")
    if st.button("Aceder Painel"):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT tipo, cnpj FROM usuarios WHERE username=? AND senha=?", (u, p))
        res = c.fetchone()
        conn.close()
        if res:
            st.session_state.update({'logado':True, 'user':u, 'tipo':res[0], 'cnpj':res[1]})
            st.rerun()
        else: st.error("Acesso negado.")

else:
    # --- INTERFACE ADMIN ---
    if st.session_state['tipo'] == 'admin':
        st.sidebar.success(f"Administrador: {st.session_state['user']}")
        opcao = st.sidebar.radio("Navegação", ["Dashboard", "Cadastrar Clientes", "Finalizar Chamados", "Segurança"])

        if opcao == "Dashboard":
            st.title("📊 Painel de Controle Up Tecnologia")
            conn = sqlite3.connect(DB_NAME)
            df = pd.read_sql_query("SELECT * FROM chamados", conn)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Chamados Ativos", len(df[df['status']=='Aberto']))
            c2.metric("Total Concluído", len(df[df['status']=='Finalizado']))
            c3.metric("Faturamento Bruto", f"R$ {df['valor'].sum():.2f}")

            st.dataframe(df, use_container_width=True)
            conn.close()

        elif opcao == "Segurança":
            st.title("💾 Gestão de Dados")
            st.info("O sistema utiliza proteção por Secrets para envio de e-mails.")
            if st.button("🚀 Disparar Backup para Nuvem (E-mail)"):
                if enviar_backup_email():
                    st.success("Backup enviado com sucesso!")
            
            with open(DB_NAME, "rb") as f:
                st.download_button("📥 Descarregar DB Local", f, file_name=f"up_backup_{datetime.now().strftime('%Y%m%d')}.db")

        # (Outras abas como 'Finalizar Chamados' seguem a mesma lógica anterior)

    # --- INTERFACE CLIENTE ---
    else:
        st.title(f"Olá, {st.session_state['user']} (Empresa: {st.session_state['cnpj']})")
        with st.form("chamado_cliente"):
            problema = st.text_area("Descreva a falha técnica ou solicitação:")
            if st.form_submit_button("Enviar para Suporte"):
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("INSERT INTO chamados (cnpj, cliente, problema, status, data_abertura, valor) VALUES (?,?,?,?,?,?)",
                          (st.session_state['cnpj'], st.session_state['user'], problema, "Aberto", datetime.now().strftime("%d/%m/%Y %H:%M"), 0.0))
                conn.commit()
                conn.close()
                st.success("Solicitação enviada com sucesso!")

    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()