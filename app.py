import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Up Tecnologia - Service Desk", layout="wide", page_icon="🛠️")

DB_NAME = 'up_tecnologia_v8.db'

# --- CSS MODERNO ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-top: 4px solid #004a99; }
    .stButton>button { border-radius: 8px; font-weight: bold; background-color: #004a99; color: white; height: 3em; }
    .status-badge { padding: 5px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS usuarios (username TEXT PRIMARY KEY, senha TEXT, cnpj TEXT, nome_empresa TEXT, cidade TEXT, gerente TEXT, tipo TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS chamados (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, cnpj TEXT, cliente TEXT, problema TEXT, 
                 status TEXT, etapa_servico TEXT, data_abertura TEXT, data_fim TEXT, valor REAL)''')
    c.execute('CREATE TABLE IF NOT EXISTS inventario (id INTEGER PRIMARY KEY AUTOINCREMENT, cnpj TEXT, empresa TEXT, equipamento TEXT, modelo TEXT, status_equip TEXT, data_inst TEXT)')
    c.execute("INSERT OR IGNORE INTO usuarios VALUES ('diogenestulio', 'DmC61ACB433@', '00.000.000/0001-00', 'Up Tecnologia', 'Sede', 'Diógenes', 'admin')")
    conn.commit()
    conn.close()

init_db()

# --- LOGIN ---
if 'logado' not in st.session_state: st.session_state['logado'] = False

if not st.session_state['logado']:
    st.markdown("<h2 style='text-align: center;'>🚀 UP TECNOLOGIA - LOGIN</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
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
            else: st.error("Acesso negado")
else:
    conn = sqlite3.connect(DB_NAME)
    
    # --- ÁREA ADMINISTRADOR ---
    if st.session_state['tipo'] == 'admin':
        # VERIFICAÇÃO DE NOVOS CHAMADOS (NOTIFICAÇÃO)
        df_notif = pd.read_sql_query("SELECT * FROM chamados WHERE status='Aberto'", conn)
        if not df_notif.empty:
            st.toast(f"🔔 Você tem {len(df_notif)} chamado(s) aguardando atendimento!", icon="🚨")

        st.sidebar.title("MENU ADMIN")
        aba = st.sidebar.radio("Navegação", ["Dashboard", "Gestão de Chamados", "Inventário", "Clientes", "Sair"])

        if aba == "Dashboard":
            st.title("📊 Painel de Controle")
            df_all = pd.read_sql_query("SELECT * FROM chamados", conn)
            c1, c2, c3 = st.columns(3)
            c1.metric("Faturamento Mensal", f"R$ {df_all['valor'].sum():.2f}")
            c2.metric("Chamados Ativos", len(df_all[df_all['status']=='Aberto']))
            c3.metric("Total de Clientes", len(pd.read_sql_query("SELECT * FROM usuarios WHERE tipo='cliente'", conn)))
            
            st.subheader("Faturamento por Unidade")
            if not df_all.empty:
                fig = px.bar(df_all.groupby('cnpj')['valor'].sum().reset_index(), x='cnpj', y='valor', color_discrete_sequence=['#004a99'])
                st.plotly_chart(fig, use_container_width=True)

        elif aba == "Gestão de Chamados":
            st.title("🛠️ Controle de Serviços")
            df_atendimento = pd.read_sql_query("SELECT * FROM chamados WHERE status='Aberto'", conn)
            
            if not df_atendimento.empty:
                id_atend = st.selectbox("Selecione o Chamado para atualizar:", df_atendimento['id'])
                nova_etapa = st.selectbox("Status do Serviço:", ["Pendente", "Em Deslocamento", "Em Atendimento", "Aguardando Peça", "Finalizado"])
                valor_final = st.number_input("Valor do Serviço (R$)", min_value=0.0)
                
                if st.button("Atualizar Status"):
                    status_geral = "Finalizado" if nova_etapa == "Finalizado" else "Aberto"
                    dt_fim = datetime.now().strftime("%d/%m/%Y %H:%M") if nova_etapa == "Finalizado" else ""
                    conn.execute("UPDATE chamados SET etapa_servico=?, valor=?, status=?, data_fim=? WHERE id=?", 
                                 (nova_etapa, valor_final, status_geral, dt_fim, id_atend))
                    conn.commit()
                    st.success(f"Chamado {id_atend} atualizado para {nova_etapa}!")
                    st.rerun()
            
            st.subheader("Histórico de Chamados")
            df_hist = pd.read_sql_query("SELECT id, cnpj, cliente, problema, etapa_servico, valor FROM chamados ORDER BY id DESC", conn)
            st.dataframe(df_hist, use_container_width=True)

        elif aba == "Inventário":
            st.title("📦 Inventário e Ativos")
            # Adicione aqui a lógica de inventário anterior (Versão V7) filtrada por CNPJ.

        elif aba == "Clientes":
            st.title("👥 Gestão de Clientes")
            # Adicione aqui o formulário de cadastro de clientes anterior.

        elif aba == "Sair":
            st.session_state['logado'] = False
            st.rerun()

    # --- ÁREA CLIENTE ---
    else:
        st.title(f"Portal do Cliente - {st.session_state['empresa']}")
        tab1, tab2 = st.tabs(["📩 Solicitar Suporte", "⏳ Acompanhar Serviço"])
        
        with tab1:
            with st.form("chamado_cli"):
                prob = st.text_area("Descreva o problema ou solicitação técnica:")
                if st.form_submit_button("Abrir Chamado"):
                    conn.execute("INSERT INTO chamados (cnpj, cliente, problema, status, etapa_servico, data_abertura, valor) VALUES (?,?,?,?,?,?,?)",
                                 (st.session_state['cnpj'], st.session_state['user'], prob, "Aberto", "Pendente", datetime.now().strftime("%d/%m/%Y %H:%M"), 0.0))
                    conn.commit()
                    st.success("Chamado aberto! Nossa equipe foi notificada.")
                    st.balloons()

        with tab2:
            st.subheader("Meus Chamados e Status em Tempo Real")
            df_meus = pd.read_sql_query(f"SELECT data_abertura, problema, etapa_servico as 'Status do Serviço' FROM chamados WHERE cnpj='{st.session_state['cnpj']}' ORDER BY id DESC", conn)
            if not df_meus.empty:
                st.table(df_meus)
            else:
                st.info("Você ainda não possui chamados registrados.")

    conn.close()
