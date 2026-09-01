"""MODULO 3 (UI) - Painel de precificacao e historico de compras (padrao Assai)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from services import pricing_service
from utils.calculations import calcular_precificacao, metricas_consolidadas


def render(usuario_ativo: str) -> None:
    st.header("📊 Precificação & Histórico de Compras")

    notas = pricing_service.listar_notas()
    if notas.empty:
        st.info("Nenhuma nota processada ainda. Use o módulo **Captura de Cupom**.")
        return

    _historico(notas)
    st.divider()

    nota_id = st.session_state.get("nota_precificacao")
    if nota_id:
        _painel_precificacao(int(nota_id))


def _historico(notas: pd.DataFrame) -> None:
    st.subheader("🧾 Histórico de notas")
    tabela = notas[
        ["id", "estabelecimento", "data_emissao", "valor_total", "forma_pagamento", "usuario_nome"]
    ].rename(
        columns={
            "id": "Nota",
            "estabelecimento": "Estabelecimento",
            "data_emissao": "Emissão",
            "valor_total": "Valor total",
            "forma_pagamento": "Pagamento",
            "usuario_nome": "Lançado por",
        }
    )
    st.dataframe(tabela, use_container_width=True, hide_index=True)

    ids = notas["id"].tolist()
    escolha = st.selectbox(
        "Abrir nota para precificar",
        ids,
        format_func=lambda i: f"#{i} — {notas.loc[notas['id']==i,'estabelecimento'].iloc[0]}",
    )
    if st.button("Abrir painel de precificação", type="primary"):
        st.session_state["nota_precificacao"] = escolha
        st.rerun()


def _painel_precificacao(nota_id: int) -> None:
    st.subheader(f"💰 Precificação — Nota #{nota_id}")
    df = pricing_service.itens_da_nota(nota_id)
    if df.empty:
        st.warning("Nota sem itens.")
        return

    base = calcular_precificacao(df)

    # --- Colunas travadas x coluna editavel ('Preço Venda') -----------------
    config_colunas = {
        "id": None,
        "nota_id": None,
        "criado_em": None,
        "codigo_ean": st.column_config.TextColumn("Código EAN", disabled=True),
        "descricao": st.column_config.TextColumn("Descrição", disabled=True, width="large"),
        "quantidade": st.column_config.NumberColumn("Qtd", disabled=True, format="%.3f"),
        "custo_unitario": st.column_config.NumberColumn(
            "Custo Unitário", disabled=True, format="R$ %.4f"
        ),
        "preco_venda": st.column_config.NumberColumn(
            "Preço Venda", min_value=0.0, step=0.01, format="R$ %.2f", required=True
        ),
        "lucro_unidade": st.column_config.NumberColumn(
            "Lucro Unidade", disabled=True, format="R$ %.2f"
        ),
        "margem_pct": st.column_config.NumberColumn("Margem %", disabled=True, format="%.2f %%"),
    }

    editado = st.data_editor(
        base,
        column_config=config_colunas,
        column_order=[
            "codigo_ean",
            "descricao",
            "quantidade",
            "custo_unitario",
            "preco_venda",
            "lucro_unidade",
            "margem_pct",
        ],
        hide_index=True,
        use_container_width=True,
        disabled=["codigo_ean", "descricao", "quantidade", "custo_unitario"],
        key=f"editor_nota_{nota_id}",
    )

    # --- Recalculo em tempo real (Pandas) ----------------------------------
    recalculado = calcular_precificacao(editado)
    m = metricas_consolidadas(recalculado)

    st.markdown("#### 📌 Métricas consolidadas")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Custo Total de Aquisição", f"R$ {m['custo_total']:,.2f}")
    c2.metric("Faturamento Projetado", f"R$ {m['faturamento_projetado']:,.2f}")
    c3.metric("Lucro Bruto Projetado", f"R$ {m['lucro_bruto_projetado']:,.2f}")
    c4.metric("Margem Média Bruta", f"{m['margem_media_bruta']:.2f} %")

    st.dataframe(
        recalculado[["descricao", "preco_venda", "lucro_unidade", "margem_pct"]],
        use_container_width=True,
        hide_index=True,
    )

    if st.button("💾 Salvar preços + atualizar Memória de Preço", type="primary"):
        pricing_service.salvar_precos_da_nota(nota_id, recalculado)
        st.success(
            "Preços salvos. As margens foram gravadas por EAN — em compras futuras "
            "o preço de venda já virá sugerido."
        )
