# streamlit_cotistas.py – versão completa e corrigida (com remoção de custos e fluxo de caixa)
# Interface de Administração de Cotistas, Custos e Relatórios de Fluxo de Caixa
# Compatível com Windows (UTF‑8)

import streamlit as st
import pandas as pd
import os
from datetime import date

# ---------------- Configurações ----------------
ARQ_COTISTAS = "cotistas.csv"
ARQ_CUSTOS   = "custos.csv"
CENTROS_CUSTO = [
    "Peão", "Veterinário", "Manejo Sanitário", "Sal",
    "Energia Elétrica", "Internet", "Manutenção de Cercas", "Alimentação", "Outros",
]

# ------------- Funções utilitárias -------------
def carregar_csv(path: str, cols: list[str]) -> pd.DataFrame:
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            for col in cols:
                if col not in df.columns:
                    df[col] = pd.NA
            return df[cols]
        except Exception as e:
            st.warning(f"Erro ao ler {path}. Criando estrutura vazia. (Detalhe: {e})")
    return pd.DataFrame(columns=cols)

def salvar_csv(df: pd.DataFrame, path: str):
    df.to_csv(path, index=False)

def total_cotas(df: pd.DataFrame) -> int:
    return int(df["Cotas"].sum()) if not df.empty else 0

def resumo_rateio(df_cot: pd.DataFrame, df_cus: pd.DataFrame, mes: int, ano: int):
    if df_cus.empty or df_cot.empty:
        return pd.DataFrame(), 0.0, 0.0
    df_cus["Data"] = pd.to_datetime(df_cus["Data"], errors="coerce")
    filtro = (df_cus["Data"].dt.month == mes) & (df_cus["Data"].dt.year == ano)
    df_mes = df_cus.loc[filtro]
    total = df_mes["Valor"].sum()
    v_cota = total / total_cotas(df_cot) if total_cotas(df_cot) else 0.0
    df_rateio = df_cot.copy()
    df_rateio["Valor a Pagar"] = df_rateio["Cotas"] * v_cota
    return df_rateio, total, v_cota

# ------------- Carregamento inicial -------------
df_cotistas = carregar_csv(ARQ_COTISTAS, ["Nome", "CPF", "Cotas", "Valor por Cota"])
df_custos   = carregar_csv(ARQ_CUSTOS,   ["Data", "Centro", "Descricao", "Valor"])

# ------------- Config Streamlit -------------
st.set_page_config(page_title="Administração de Cotistas", layout="wide")
st.title("Administração de Cotistas & Rateio de Custos")

menu = st.sidebar.radio(
    "Selecionar módulo:",
    [
        "Cotistas",
        "Custos",
        "Fluxo por 1 Cota (72 meses)",
        "Fluxo para 10 Cotas (72 meses)",
    ],
    index=0,
)

# ================================================================
# GUIA 1 – Cotistas
# ================================================================
if menu == "Cotistas":
    st.sidebar.header("Adicionar / Editar Cotista")
    with st.sidebar.form("form_cotista"):
        nome = st.text_input("Nome completo")
        cpf  = st.text_input("CPF")
        qtd  = st.number_input("Nº de cotas", min_value=1, step=1)
        valor = st.number_input("Valor por cota (R$)", min_value=0.0, step=100.0, format="%.2f")
        salvar = st.form_submit_button("Salvar / Atualizar")

    if salvar and nome and cpf:
        novo = pd.DataFrame([[nome, cpf, qtd, valor]], columns=df_cotistas.columns)
        df_cotistas = df_cotistas[df_cotistas["CPF"] != cpf]
        df_cotistas = pd.concat([df_cotistas, novo], ignore_index=True)
        salvar_csv(df_cotistas, ARQ_COTISTAS)
        st.success("Cotista salvo com sucesso!")
        st.rerun()

    col1, col2 = st.columns(2)
    col1.metric("Total de Cotas", total_cotas(df_cotistas))
    capital = (df_cotistas["Cotas"] * df_cotistas["Valor por Cota"]).sum()
    col2.metric("Capital Aportado", f"R$ {capital:,.2f}")

    st.subheader("Lista de Cotistas")
    tabela_edit = st.data_editor(df_cotistas, use_container_width=True)
    if st.button("Salvar Alterações"):
        df_cotistas = tabela_edit.copy()
        salvar_csv(df_cotistas, ARQ_COTISTAS)
        st.success("Alterações salvas!")
        st.rerun()

    st.divider()
    st.subheader("Remover Cotista")
    cpfs = df_cotistas["CPF"].tolist()
    if cpfs:
        escolhido = st.selectbox("CPF:", cpfs)
        if st.button("Remover"):
            df_cotistas = df_cotistas[df_cotistas["CPF"] != escolhido]
            salvar_csv(df_cotistas, ARQ_COTISTAS)
            st.success("Cotista removido!")
            st.rerun()
    else:
        st.info("Nenhum cotista cadastrado.")

# ================================================================
# GUIA 2 – Custos
# ================================================================
elif menu == "Custos":
    st.sidebar.header("Lançar Custo Operacional")
    with st.sidebar.form("form_custo"):
        data  = st.date_input("Data", value=date.today())
        centro = st.selectbox("Centro de Custo", CENTROS_CUSTO)
        desc  = st.text_input("Descrição")
        valor = st.number_input("Valor (R$)", min_value=0.0, step=100.0, format="%.2f")
        add = st.form_submit_button("Registrar Custo")

    if add and valor > 0:
        novo = pd.DataFrame([[data, centro, desc, valor]], columns=df_custos.columns)
        df_custos = pd.concat([df_custos, novo], ignore_index=True)
        salvar_csv(df_custos, ARQ_CUSTOS)
        st.success("Custo registrado!")
        st.rerun()

    st.subheader("Rateio por Período")
    ano = st.selectbox("Ano", sorted({date.today().year}))
    mes = st.selectbox("Mês", list(range(1, 13)), index=date.today().month - 1)
    df_rateio, tot, v_cota = resumo_rateio(df_cotistas, df_custos, int(mes), int(ano))

    col1, col2 = st.columns(2)
    col1.metric("Total de Custos", f"R$ {tot:,.2f}")
    col2.metric("Valor por Cota", f"R$ {v_cota:,.2f}")

    if df_rateio.empty:
        st.info("Sem dados para este período.")
    else:
        st.dataframe(df_rateio[["Nome", "CPF", "Cotas", "Valor a Pagar"]], use_container_width=True)

    st.divider()
    st.subheader("Custos Lançados")
    st.dataframe(df_custos, use_container_width=True)

    st.divider()
    st.subheader("Remover custos")
    descricao_filter = st.text_input("Descrição contém:")
    data_filter = st.date_input("Data específica:", value=None)
    centro_options = ["Todos"] + sorted(set(df_custos["Centro"].dropna().unique()))
    centro_filter = st.selectbox("Centro de custo:", centro_options)

    df_filtrado = df_custos.copy()
    df_filtrado["Data"] = pd.to_datetime(df_filtrado["Data"], errors="coerce")

    if descricao_filter:
        df_filtrado = df_filtrado[df_filtrado["Descricao"].str.contains(descricao_filter, case=False)]
    if data_filter:
        df_filtrado = df_filtrado[df_filtrado["Data"].dt.date == data_filter]
    if centro_filter != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Centro"] == centro_filter]

    if df_filtrado.empty:
        st.info("Nenhum custo encontrado com os filtros aplicados.")
    else:
        df_filtrado = df_filtrado.reset_index(drop=True)
        df_filtrado["Selecionar"] = False

        edited_df = st.data_editor(
            df_filtrado,
            column_config={"Selecionar": st.column_config.CheckboxColumn("Selecionar")},
            hide_index=True,
            key="editor_remocao"
        )
        selecionados = edited_df[edited_df["Selecionar"] == True]

        if st.button("Remover Selecionados"):
            if selecionados.empty:
                st.info("Nenhum custo selecionado para remover.")
            else:
                df_custos = df_custos.merge(selecionados.drop(columns=["Selecionar"]), how="left", indicator=True)
                df_custos = df_custos[df_custos["_merge"] == "left_only"].drop(columns=["_merge"])
                salvar_csv(df_custos, ARQ_CUSTOS)
                st.success("Custos removidos com sucesso!")
                st.rerun()

# ================================================================
# GUIA 3 – Fluxo por 1 Cota
# ================================================================
elif menu == "Fluxo por 1 Cota (72 meses)":
    st.header("Fluxo de Caixa por Cota (10 Vacas de Cria) - Horizonte de 4 Ciclos (72 meses)")
    st.markdown("""
    **Parâmetros:**  
    Prenhez 80%; 50% machos / 50% fêmeas; 50% dos machos vendidos a 160 kg, 50% a 320 kg;  
    Fêmeas retidas e inseminadas aos 250 kg (R$ 100 cada).  
    Preço de compra: **R$ 12,08/kg**  Preço de venda: **R$ 10,60/kg**  
    Custo de manutenção: **R$ 238,75 por mês**
    """)

    st.markdown("""
    | Ciclo | Vacas iniciais | Nascimentos | Machos (160/320kg) | Fêmeas retidas | Vacas finais |
    |-----|-----|-----|-----|-----|-----|
    | 1 | 10 | 8 | 2 / 2 | 4 | 14 |
    | 2 | 14 | 11,2 | 2,8 / 2,8 | 5,6 | 19,6 |
    | 3 | 19,6 | 15,7 | 3,9 / 3,9 | 7,8 | 27,4 |
    | 4 | 27,4 | 22 | 5,5 / 5,5 | 11 | 38,4 |
    """)

    st.markdown("""
    **Receitas com machos:** 10.176 + 14.250 + 19.958 + 27.933 = **R$ 72.317**

    **Custos (72 meses):** Compra 10 novilhas R$ 19.328 • Manutenção R$ 17.190 • Inseminações R$ 2.840  
    **Lucro líquido por cota:** **R$ 32.959** em 72 meses
    """)

# ================================================================
# GUIA 4 – Fluxo para 10 Cotas
# ================================================================
elif menu == "Fluxo para 10 Cotas (72 meses)":
    st.header("Fluxo de Caixa para 10 Cotas (100 Vacas de Cria) - Horizonte de 4 Ciclos (72 meses)")

    st.markdown("""
    ### Crescimento do Rebanho Fêmea

    | Ciclo | Vacas início | Vacas fim |
    |-------|--------------|-----------|
    | 1     | 100          | 140       |
    | 2     | 140          | 196       |
    | 3     | 196          | 274       |
    | 4     | 274          | 384       |

    ### Receita com venda de machos (10 cotas)

    - Ciclo 1: 25.440
    - Ciclo 2: 35.625
    - Ciclo 3: 49.895
    - Ciclo 4: 69.832

    **Total Receita:** R$ 180.792

    **Custos:**
    - Compra de 100 novilhas: R$ 193.280
    - Manutenção por 72 meses: R$ 171.900
    - Inseminações: R$ 28.400

    **Lucro líquido consolidado:** **R$ 214.788**
    """)
