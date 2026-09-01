"""MODULO 4 (UI) - Dashboard multiusuario (divisao por pessoa)."""
from __future__ import annotations

import plotly.express as px
import streamlit as st

from services import finance_service
from utils.calculations import mes_atual_str


def render(usuario_ativo: str) -> None:
    st.header("👥 Dashboard de Performance — Divisão por Pessoa")

    mes = st.text_input("Mês de referência (AAAA-MM)", mes_atual_str())

    por_pessoa = finance_service.gastos_por_pessoa(mes)
    por_categoria = finance_service.gastos_por_categoria(mes)

    if por_pessoa.empty and por_categoria.empty:
        st.info("Sem lançamentos neste mês.")
        return

    total = float(por_pessoa["valor"].sum()) if not por_pessoa.empty else 0.0
    st.metric("Gasto total do mês", f"R$ {total:,.2f}")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Gastos por categoria")
        if not por_categoria.empty:
            fig = px.pie(
                por_categoria,
                names="categoria",
                values="valor",
                hole=0.35,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Gastos por pessoa (auditoria)")
        if not por_pessoa.empty:
            fig = px.bar(
                por_pessoa,
                x="usuario_nome",
                y="valor",
                color="usuario_nome",
                text_auto=".2s",
                labels={"usuario_nome": "Pessoa", "valor": "R$"},
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Tabela detalhada")
    st.dataframe(
        por_pessoa.rename(columns={"usuario_nome": "Pessoa", "valor": "Total (R$)"}),
        use_container_width=True,
        hide_index=True,
    )
