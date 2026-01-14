import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime
import re
from pathlib import Path
from io import BytesIO

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
    # Inserir Administrador Geral fixo
    c.execute("""INSERT OR IGNORE INTO usuarios (username, senha, cnpj, nome_completo, tipo)
                 VALUES (?,?,?,?,?)""",
              ("diogenestulio", "DmC61ACB433@", "11.881.099/0001-02", "Diógenes Túlio", "admin"))
    conn.commit()
    conn.close()

init_db()

# -----------------------------
# UTILITÁRIOS
# -----------------------------
def formatar_cnpj(cnpj: str) -> str:
    numeros = re.sub(r"\D", "", cnpj)
    if len(numeros) > 14:
        numeros = numeros[:14]
    if len(numeros) < 14:
        return numeros
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
        st.markdown(
            f"""
            <div style="padding:16px; backdrop-filter: blur(8px); background:{GLASS}; border-radius:16px; border:1px solid #eaeaea;">
                <h2 style="margin:0; color:{PRIMARY};">Up Tecnologia Ltda</h2>
                <p style="margin:0; color:{ACCENT};">HelpDesk • Portal Futurista</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_user:
        if st.session_state.get("auth"):
            st.markdown(
                f"""
                <div style="padding:12px; background:{BG_LIGHT}; border-radius:12px; border:1px solid #eaeaea;">
                    <strong>Usuário:</strong> {st.session_state['auth']['nome']}<br>
                    <strong>Perfil:</strong> {st.session_state['auth']['tipo']}<br>
                    <strong>CNPJ:</strong> {st.session_state['auth']['cnpj']}
                </div>
                """,
                unsafe_allow_html=True
            )

def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Dados") -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

# -----------------------------
# LOGIN
# -----------------------------
if "auth" not in st.session_state:
    st.session_state["auth"] = None

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
            st.rerun()
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
    st.rerun()

perfil = st.session_state["auth"]["tipo"]
cnpj_user = st.session_state["auth"]["cnpj"]
menu = st.sidebar.radio("Navegação", ["Abrir Chamado", "Kanban de Chamados", "Cadastro Empresa/Responsável", "Financeiro", "Dashboard", "Exportar Dados"])

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
            conn.execute(
                """INSERT INTO chamados (cnpj, autor, problema, status, etapa, data_abertura, valor)
                   VALUES (?,?,?,?,?,?,?)""",
                (cnpj_user, st.session_state["auth"]["nome"], desc.strip(),
                 "Aberto", "Pendente", datetime.now().strftime("%d/%m/%Y %H:%M"), 0.0)
            )
            conn.commit()
            conn.close()
            st.success("Chamado enviado! Você pode acompanhar no Kanban.")
            st.balloons()
        elif enviar:
            st.error("Por favor, descreva o problema.")

    st.markdown(
        f"""
        <div style="margin-top:16px; padding:12px; background:{BG_LIGHT}; border-radius:12px; border:1px solid #eaeaea;">
            <strong>Transparência:</strong> Seu chamado aparece no Kanban com status, etapa, data/hora, valor e autor.
        </div>
        """,
        unsafe_allow_html=True
    )

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

    if perfil == "admin":
        st.divider()
        st.markdown("#### Atualizar status/etapa de um chamado")
        conn = get_conn()
        ids = pd.read_sql_query("SELECT id FROM chamados ORDER BY id DESC", conn)["id"].tolist()
        conn.close()
        if ids:
            sel = st.selectbox("ID do chamado", ids)
            novo_status = st.selectbox("Novo status", ["Aberto", "Em Andamento", "Finalizado"])
            nova_etapa = st.selectbox("Nova etapa", ["Pendente", "Técnico a Caminho", "Em Manutenção", "Aguardando Peça", "Concluído"])
            novo_valor = st.number_input("Valor (R$)", min_value=0.0, step=50.0)
            if st.button("Salvar atualização", type="primary"):
                conn = get_conn()
                conn.execute("UPDATE chamados SET status=?, etapa=?, valor=? WHERE id=?", (novo_status, nova_etapa, novo_valor, sel))
                conn.commit()
                conn.close()
                st.success("Chamado atualizado!")
                st.rerun()
        else:
            st.info("Não há chamados para atualizar.")

# -----------------------------
# CADASTRO EMPRESA/RESPONSÁVEL
# -----------------------------
elif menu == "Cadastro Empresa/Responsável":
    if perfil != "admin":
        st.warning("Apenas administradores podem acessar esta área.")
    else:
        st.subheader("🏢 Cadastro Rápido • Empresa + Responsável")
        with st.form("cadastro_completo"):
            cnpj_input = st.text_input("CNPJ (digite apenas números)")
            cnpj = formatar_cnpj(cnpj_input)
            st.write(f"📌 CNPJ formatado: **{cnpj}**")
            nome = st.text_input("Nome Fantasia")
            cidade = st.text_input("Cidade")
            gerente = st.text_input("Gerente")
            usuario = st.text_input("Login (Username)")
            senha = st.text_input("Senha Inicial", type="password")
            nome_resp = st.text_input("Nome do Responsável")
            finalizar = st.form_submit_button("✅ Finalizar Cadastro", type="primary")
            if finalizar:
                if not validar_cnpj(cnpj):
                    st.error("⚠️ CNPJ inválido! Use o formato 00.000.000/0001-00.")
                elif cnpj and nome and usuario and senha and nome_resp:
                    try:
                        conn = get_conn()
                        conn.execute("INSERT INTO empresas VALUES (?,?,?,?)", (cnpj, nome, cidade, gerente))
                        conn.execute("INSERT INTO usuarios VALUES (?,?,?,?,?)", (usuario, senha, cnpj, nome_resp, 'cliente'))
                        conn.commit()
                        conn.close()
                        st.success("🎉 Empresa e responsável cadastrados!")
                        st.balloons()
                    except sqlite3.IntegrityError:
                        st.error("⚠️ Empresa ou usuário já existem.")
                else:
                    st.error("⚠️ Preencha todos os campos obrigatórios.")

        st.divider()
        st.markdown("#### Edição rápida")
        conn = get_conn()
        df_emp = pd.read_sql_query("SELECT * FROM empresas", conn)
        df_usr = pd.read_sql_query("SELECT username, nome_completo, cnpj, tipo FROM usuarios", conn)
        conn.close()

        edited_emp = st.data_editor(df_emp, use_container_width=True, num_rows="dynamic")
        edited_usr = st.data_editor(df_usr[df_usr["tipo"] != "admin"], use_container_width=True, num_rows="dynamic")

        colS1, colS2 = st.columns(2)
        with colS1:
            if st.button("💾 Salvar empresas"):
                conn = get_conn()
                conn.execute("DELETE FROM empresas")
                for _, r in edited_emp.iterrows():
                    conn.execute("INSERT INTO empresas VALUES (?,?,?,?)", (r["cnpj"], r["nome_empresa"], r["cidade"], r["gerente_geral"]))
                conn.commit()
                conn.close()
                st.success("Empresas atualizadas!")
        with colS2:
            if st.button("💾 Salvar usuários"):
                conn = get_conn()
                conn.execute("DELETE FROM usuarios WHERE tipo!='admin'")
                for _, r in edited_usr.iterrows():
                    conn.execute(
                        """INSERT OR REPLACE INTO usuarios (username, senha, cnpj, nome_completo, tipo)
                           VALUES (?,?,?,?,?)""",
                        (r["username"], "SenhaInicial123!", r["cnpj"], r["nome_completo"], r["tipo"])
                    )
                conn.commit()
                conn.close()
                st.success("Usuários atualizados!")

# -----------------------------
# FINANCEIRO (Fechamento por CNPJ e Mês)
# -----------------------------
elif menu == "Financeiro":
    if perfil != "admin":
        st.warning("Apenas administradores podem acessar esta área.")
    else:
        st.subheader("💰 Financeiro • Fechamento por CNPJ e Mês")
        conn = get_conn()
        empresas = pd.read_sql_query("SELECT cnpj, nome_empresa FROM empresas", conn)
        conn.close()

        if empresas.empty:
            st.info("Cadastre empresas para gerar relatórios financeiros.")
        else:
            cnpj_sel = st.selectbox("Selecione o CNPJ", empresas["cnpj"].tolist())
            mes = st.selectbox("Mês", [f"{m:02d}" for m in range(1, 13)])
            ano = st.selectbox("Ano", [datetime.now().year, datetime.now().year - 1, datetime.now().year - 2])

            conn = get_conn()
            df_fin = pd.read_sql_query("SELECT * FROM chamados WHERE cnpj=?", conn, params=(cnpj_sel,))
            conn.close()

            def match_mes_ano(s):
                try:
                    dt = datetime.strptime(s, "%d/%m/%Y %H:%M")
                    return dt.month == int(mes) and dt.year == int(ano)
                except:
                    return False

            df_fin = df_fin[df_fin["data_abertura"].apply(match_mes_ano)]

            st.markdown(
                f"""
                <div style="padding:12px; backdrop-filter: blur(6px); background:{GLASS}; border-radius:12px; border:1px solid #eaeaea;">
                    <strong>Período:</strong> {mes}/{ano} • <strong>CNPJ:</strong> {cnpj_sel}<br>
                    <strong>Total de chamados:</strong> {len(df_fin)} • <strong>Receita:</strong> R$ {df_fin['valor'].sum():.2f}
                </div>
                """,
                unsafe_allow_html=True
            )

            if not df_fin.empty:
                st.markdown("#### Detalhes do fechamento")
                cols = ["id", "data_abertura", "autor", "problema", "status", "etapa", "valor"]
                st.dataframe(df_fin[cols], use_container_width=True)

                fig_val = px.bar(
                    df_fin, x="data_abertura", y="valor", color="status",
                    title="Valores por chamado (linha do tempo)",
                    color_discrete_sequence=[PRIMARY, ACCENT]
                )
                st.plotly_chart(fig_val, use_container_width=True)

                # Exportações
                colE1, colE2 = st.columns(2)
                with colE1:
                    csv_bytes = df_fin.to_csv(index=False).encode("utf-8")
                    st.download_button("⬇️ Baixar fechamento (CSV)", data=csv_bytes, file_name=f"fechamento_{cnpj_sel}_{mes}_{ano}.csv", mime="text/csv")
                with colE2:
                    xls_bytes = to_excel_bytes(df_fin, sheet_name="Fechamento")
                    st.download_button("⬇️ Baixar fechamento (Excel)", data=xls_bytes, file_name=f"fechamento_{cnpj_sel}_{mes}_{ano}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("Sem chamados para o período selecionado.")

# -----------------------------
# DASHBOARD
# -----------------------------
elif menu == "Dashboard":
    st.subheader("📊 Painel Futurista")
    conn = get_conn()
    if perfil == "admin":
        df_ch = pd.read_sql_query("SELECT * FROM chamados", conn)
        df_emp = pd.read_sql_query("SELECT * FROM empresas", conn)
        df_usr = pd.read_sql_query("SELECT * FROM usuarios", conn)
    else:
        df_ch = pd.read_sql_query("SELECT * FROM chamados WHERE cnpj=?", conn, params=(cnpj_user,))
        df_emp = pd.read_sql_query("SELECT * FROM empresas WHERE cnpj=?", conn, params=(cnpj_user,))
        df_usr = pd.read_sql_query("SELECT * FROM usuarios WHERE cnpj=?", conn, params=(cnpj_user,))
    conn.close()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Chamados", len(df_ch))
    col2.metric("Finalizados", len(df_ch[df_ch["status"] == "Finalizado"]))
    col3.metric("Pendentes", len(df_ch[df_ch["status"] != "Finalizado"]))
    col4.metric("Receita (R$)", f"{df_ch['valor'].sum():.2f}")

    if not df_ch.empty:
        fig1 = px.bar(
            df_ch.groupby("status")["id"].count().reset_index(),
            x="status", y="id", title="Chamados por Status",
            color="status", color_discrete_sequence=[PRIMARY, ACCENT]
        )
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.pie(
            df_ch, names="etapa", title="Distribuição por Etapa",
            color_discrete_sequence=px.colors.sequential.Blues
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Sem dados para exibir.")

# -----------------------------
# EXPORTAR DADOS (Clientes, Movimentação, Financeiro)
# -----------------------------
elif menu == "Exportar Dados":
    st.subheader("⬇️ Exportar Dados")
    conn = get_conn()
    df_emp = pd.read_sql_query("SELECT * FROM empresas", conn)
    df_usr = pd.read_sql_query("SELECT * FROM usuarios", conn)
    df_ch = pd.read_sql_query("SELECT * FROM chamados", conn)
    conn.close()

    st.markdown("#### Clientes (Empresas)")
    st.dataframe(df_emp, use_container_width=True)
    colC1, colC2 = st.columns(2)
    with colC1:
        st.download_button("⬇️ Empresas (CSV)", data=df_emp.to_csv(index=False).encode("utf-8"), file_name="empresas.csv", mime="text/csv")
    with colC2:
        st.download_button("⬇️ Empresas (Excel)", data=to_excel_bytes(df_emp, "Empresas"), file_name="empresas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.markdown("#### Usuários")
    st.dataframe(df_usr, use_container_width=True)
    colU1, colU2 = st.columns(2)
    with colU1:
        st.download_button("⬇️ Usuários (CSV)", data=df_usr.to_csv(index=False).encode("utf-8"), file_name="usuarios.csv", mime="text/csv")
    with colU2:
        st.download_button("⬇️ Usuários (Excel)", data=to_excel_bytes(df_usr, "Usuarios"), file_name="usuarios.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.markdown("#### Chamados (Movimentação)")
    st.dataframe(df_ch, use_container_width=True)
    colM1, colM2 = st.columns(2)
    with colM1:
        st.download_button("⬇️ Chamados (CSV)", data=df_ch.to_csv(index=False).encode("utf-8"), file_name="chamados.csv", mime="text/csv")
    with colM2:
        st.download_button("⬇️ Chamados (Excel)", data=to_excel_bytes(df_ch, "Chamados"), file_name="chamados.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")