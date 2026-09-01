"""Modulo auxiliar - Configuracoes: cartoes e teto de orcamento."""
from __future__ import annotations

import streamlit as st

from services import finance_service
from utils.calculations import mes_atual_str


def render(usuario_ativo: str) -> None:
    st.header("🛠️ Configurações")

    aba_cartoes, aba_orcamento = st.tabs(["💳 Cartões", "🎯 Orçamento (teto)"])

    with aba_cartoes:
        _cartoes()

    with aba_orcamento:
        _orcamento()


def _cartoes() -> None:
    df = finance_service.listar_cartoes()
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.subheader("Adicionar / editar cartão")
    with st.form("form_cartao", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome", placeholder="Cartão Inter")
        bandeira = c2.text_input("Bandeira", placeholder="Visa / Master")
        c3, c4 = st.columns(2)
        limite_total = c3.number_input("Limite total (R$)", min_value=0.0, step=100.0)
        limite_disp = c4.number_input("Limite disponível (R$)", min_value=0.0, step=100.0)
        c5, c6 = st.columns(2)
        fechamento = c5.number_input("Dia de fechamento", 1, 31, 20)
        vencimento = c6.number_input("Dia de vencimento", 1, 31, 28)

        if st.form_submit_button("Salvar cartão", type="primary"):
            finance_service.salvar_cartao(
                {
                    "nome": nome,
                    "bandeira": bandeira,
                    "limite_total": limite_total,
                    "limite_disponivel": limite_disp,
                    "dia_fechamento": int(fechamento),
                    "dia_vencimento": int(vencimento),
                }
            )
            st.success("Cartão salvo.")
            st.rerun()


def _orcamento() -> None:
    mes = st.text_input("Mês (AAAA-MM)", mes_atual_str())
    atual = finance_service.get_teto(mes)
    novo = st.number_input("Teto de gastos do mês (R$)", min_value=0.0, value=float(atual), step=100.0)
    if st.button("Salvar teto", type="primary"):
        finance_service.set_teto(novo, mes)
        st.success("Teto atualizado.")

    info = finance_service.verificar_estouro_orcamento(mes)
    st.metric(
        "Gasto atual x teto",
        f"R$ {info['gasto']:,.2f}",
        f"{info['percentual']:.0f}% do teto",
        delta_color="inverse",
    )
