import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Up Tecnologia - Enterprise", layout="wide", page_icon="🏢")

DB_NAME = 'up_tecnologia_v9.db'

# --- DATABASE ENGINE ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Tabela de Empresas
    c.execute('''CREATE TABLE IF NOT EXISTS empresas 
                 (cnpj TEXT PRIMARY KEY, nome_empresa TEXT, cidade TEXT, gerente_geral TEXT)''')
    # Tabela de Usuários (Vários por CNPJ)
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios 
                 (username TEXT PRIMARY KEY, senha TEXT, cnpj TEXT, nome_completo TEXT, tipo TEXT,
                  FOREIGN KEY(cnpj) REFERENCES empresas(cnpj))''')
    # Tabela de Chamados
    c.execute('''CREATE TABLE IF NOT EXISTS chamados 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, cnpj TEXT, autor TEXT, problema TEXT, 
                  status TEXT, etapa TEXT, data_abertura TEXT, valor REAL)''')
    
    # Admin Padrão
    c.execute("INSERT OR IGNORE INTO usuarios VALUES ('diogenestulio', 'DmC61ACB433@', '00.000.000/0001-00', 'Diógenes Túlio', 'admin')")
    conn.commit()
    conn.close()

init_db()

# --- INTERFACE DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.update({'logado': False, 'user': None, 'tipo': None, 'cnpj': None, 'nome': None})

if not st.session_state['logado']:
    st.title("🛡️ Up Tecnologia - Acesso Restrito")
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("SELECT tipo, cnpj, nome_completo FROM usuarios WHERE username=? AND senha=?", (u, p))
            res = c.fetchone()
            if res:
                st.session_state.update({'logado': True, 'user': u, 'tipo': res[0], 'cnpj': res[1], 'nome': res[2]})
                st.rerun()
            else: st.error("Credenciais incorretas.")
else:
    conn = sqlite3.connect(DB_NAME)
    
    # --- ÁREA ADMINISTRADOR ---
    if st.session_state['tipo'] == 'admin':
        # NOTIFICAÇÃO PARA O ADM
        novos = pd.read_sql_query("SELECT id FROM chamados WHERE status='Aberto'", conn)
        if len(novos) > 0:
            st.toast(f"🚨 Existem {len(novos)} chamados pendentes!", icon="🔥")

        st.sidebar.title("Painel Gestor")
        menu = st.sidebar.radio("Navegação", ["Dashboard", "Gestão de Chamados", "Cadastrar Empresa/Contatos", "Lista de Clientes"])

        if menu == "Dashboard":
            st.title("📊 Visão Geral")
            df_ch = pd.read_sql_query("SELECT * FROM chamados", conn)
            c1, c2, c3 = st.columns(3)
            c1.metric("Receita", f"R$ {df_ch['valor'].sum():.2f}")
            c2.metric("Chamados", len(df_ch))
            c3.metric("Clientes", len(pd.read_sql_query("SELECT * FROM empresas", conn)))
            
        elif menu == "Cadastrar Empresa/Contatos":
            st.title("🏢 Cadastro Estruturado")
            
            tab_emp, tab_user = st.tabs(["Nova Empresa", "Novo Usuário (Responsável)"])
            
            with tab_emp:
                with st.form("form_emp"):
                    c1, c2 = st.columns(2)
                    e_cnpj = c1.text_input("CNPJ da Unidade")
                    e_nome = c2.text_input("Nome Fantasia")
                    e_cid = c1.text_input("Cidade")
                    e_ger = c2.text_input("Gerente da Unidade")
                    if st.form_submit_button("Salvar Empresa"):
                        conn.execute("INSERT INTO empresas VALUES (?,?,?,?)", (e_cnpj, e_nome, e_cid, e_ger))
                        conn.commit()
                        st.success("Empresa cadastrada!")

            with tab_user:
                with st.form("form_usr"):
                    df_emp = pd.read_sql_query("SELECT nome_empresa, cnpj FROM empresas", conn)
                    u_emp = st.selectbox("Vincular ao CNPJ", df_emp['cnpj'].tolist())
                    u_nome = st.text_input("Nome do Responsável")
                    u_login = st.text_input("Login (Username)")
                    u_pass = st.text_input("Senha Inicial")
                    if st.form_submit_button("Criar Acesso"):
                        conn.execute("INSERT INTO usuarios VALUES (?,?,?,?,?)", (u_login, u_pass, u_emp, u_nome, 'cliente'))
                        conn.commit()
                        st.success(f"Acesso criado para {u_nome}!")

        elif menu == "Gestão de Chamados":
            st.title("🛠️ Controle de Atendimento")
            df_abertos = pd.read_sql_query("SELECT * FROM chamados WHERE status='Aberto'", conn)
            if not df_abertos.empty:
                sel = st.selectbox("Chamado ID", df_abertos['id'])
                nova_etapa = st.selectbox("Status", ["Pendente", "Técnico a Caminho", "Em Manutenção", "Aguardando Peça", "Finalizado"])
                valor = st.number_input("Valor do Serviço", min_value=0.0)
                if st.button("Atualizar Chamado"):
                    st_final = "Finalizado" if nova_etapa == "Finalizado" else "Aberto"
                    conn.execute("UPDATE chamados SET etapa=?, valor=?, status=? WHERE id=?", (nova_etapa, valor, st_final, sel))
                    conn.commit()
                    st.success("Status atualizado!")
                    st.rerun()
            st.dataframe(df_abertos, use_container_width=True)

    # --- ÁREA CLIENTE (USUÁRIO RESPONSÁVEL) ---
    else:
        # NOTIFICAÇÃO PARA O CLIENTE
        st.toast(f"Olá {st.session_state['nome']}, acompanhe seus pedidos abaixo.", icon="👋")
        
        st.title(f"Portal de Chamados - CNPJ: {st.session_state['cnpj']}")
        
        t_novo, t_status = st.tabs(["➕ Abrir Chamado", "📋 Meus Pedidos"])
        
        with t_novo:
            with st.form("novo_ch"):
                desc = st.text_area("Descreva o problema ou solicitação técnica")
                if st.form_submit_button("Enviar para Up Tecnologia"):
                    conn.execute("INSERT INTO chamados (cnpj, autor, problema, status, etapa, data_abertura, valor) VALUES (?,?,?,?,?,?,?)",
                                 (st.session_state['cnpj'], st.session_state['nome'], desc, "Aberto", "Pendente", datetime.now().strftime("%d/%m %H:%M"), 0.0))
                    conn.commit()
                    st.success("Chamado enviado! Diógenes será notificado.")
                    st.balloons()
        
        with t_status:
            st.subheader("Status das suas solicitações")
            # Aqui ele vê todos os chamados abertos por QUALQUER pessoa do mesmo CNPJ
            df_cli = pd.read_sql_query(f"SELECT data_abertura, autor, problema, etapa FROM chamados WHERE cnpj='{st.session_state['cnpj']}' ORDER BY id DESC", conn)
            st.table(df_cli)

    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()
    conn.close()