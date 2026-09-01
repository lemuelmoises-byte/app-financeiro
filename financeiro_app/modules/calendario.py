"""MODULO 2 (UI) - Calendario financeiro, cartoes e alertas de fluxo de caixa."""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st
from streamlit_calendar import calendar

from services import finance_service
from services.usuarios_service import id_do_usuario, listar_usuarios

_OPCOES_CAL = {
    "initialView": "dayGridMonth",
    "locale": "pt-br",
    "height": 620,
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,listMonth",
    },
    "dayMaxEvents": 3,
}


def render(usuario_ativo: str) -> None:
    st.header("🗓️ Calendário Financeiro — Fluxo de Caixa")

    _indicador_cartoes()
    st.divider()

    col_cal, col_dia = st.columns([3, 2], gap="large")

    with col_cal:
        eventos = finance_service.eventos_calendario(apenas_pendentes=True)
        estado = calendar(events=eventos, options=_OPCOES_CAL, key="calendario_financeiro")

        dia_sel = None
        if estado.get("dateClick"):
            dia_sel = estado["dateClick"]["date"][:10]
        elif estado.get("eventClick"):
            dia_sel = estado["eventClick"]["event"]["start"][:10]
        if dia_sel:
            st.session_state["dia_selecionado"] = dia_sel

    with col_dia:
        _detalhe_do_dia(st.session_state.get("dia_selecionado"))

    st.divider()
    _form_nova_conta(usuario_ativo)


def _indicador_cartoes() -> None:
    resumo = finance_service.resumo_cartoes()
    if not resumo:
        st.info("Nenhum cartão cadastrado. Cadastre em **Configurações → Cartões**.")
        return

    st.subheader("💳 Cartões — limite e melhor dia de compra")
    cols = st.columns(len(resumo))
    for col, c in zip(cols, resumo):
        uso = 100 * (1 - (c["limite_disponivel"] / c["limite_total"])) if c["limite_total"] else 0
        with col:
            st.markdown(f"**{c['nome']}**")
            st.metric("Limite disponível", f"R$ {c['limite_disponivel']:,.2f}")
            st.progress(min(max(uso / 100, 0), 1.0), text=f"{uso:.0f}% usado")
            st.caption(
                f"Fecha dia {c['dia_fechamento']} · vence dia {c['dia_vencimento']}"
            )
            st.success(f"🟢 Melhor dia de compra: **{c['melhor_dia_compra'].strftime('%d/%m/%Y')}**")


def _detalhe_do_dia(dia_iso: str | None) -> None:
    st.subheader("📌 Detalhamento do dia")
    if not dia_iso:
        st.caption("Clique em um dia no calendário para ver as contas linha a linha.")
        return

    dia = date.fromisoformat(dia_iso)
    df = finance_service.despesas_do_dia(dia)
    st.markdown(f"### {dia.strftime('%d/%m/%Y')}")

    if df.empty:
        st.info("Sem contas para esta data.")
        return

    with st.container(border=True):
        for _, linha in df.iterrows():
            c1, c2, c3 = st.columns([3, 2, 2])
            pago = linha["status"] == "Pago"
            c1.markdown(
                f"{'✅' if pago else '🔴'} **{linha['descricao']}**  \n"
                f"<small>{linha.get('categoria','')} · {linha.get('usuario_nome') or '—'}</small>",
                unsafe_allow_html=True,
            )
            c2.markdown(f"**R$ {linha['valor']:,.2f}**")
            if not pago:
                if c3.button("💸 Dar baixa", key=f"baixa_{linha['id']}"):
                    finance_service.dar_baixa(int(linha["id"]))
                    st.toast("Conta marcada como paga.")
                    st.rerun()
            else:
                c3.caption("Pago")

        total = df["valor"].sum()
        pendente = df[df["status"] == "Pendente"]["valor"].sum()
        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("Total do dia", f"R$ {total:,.2f}")
        m2.metric("Ainda pendente", f"R$ {pendente:,.2f}")


def _form_nova_conta(usuario_ativo: str) -> None:
    with st.expander("➕ Lançar nova conta / despesa futura"):
        with st.form("nova_conta", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            descricao = c1.text_input("Descrição", placeholder="Ex: Conta de água")
            valor = c2.number_input("Valor (R$)", min_value=0.0, step=10.0)
            venc = c3.date_input("Vencimento", date.today())

            c4, c5, c6 = st.columns(3)
            categoria = c4.text_input("Categoria", "Contas fixas")
            nomes = [u["nome"] for u in listar_usuarios()]
            responsavel = c5.selectbox(
                "Responsável", nomes, index=nomes.index(usuario_ativo) if usuario_ativo in nomes else 0
            )
            cartoes = finance_service.listar_cartoes()
            opc_cartao = ["— nenhum —"] + (cartoes["nome"].tolist() if not cartoes.empty else [])
            cartao_nome = c6.selectbox("Cartão (opcional)", opc_cartao)

            agenda = st.checkbox("Criar lembrete no Google Agenda (1 dia antes)", value=True)

            if st.form_submit_button("Salvar conta", type="primary"):
                cartao_id = None
                if cartao_nome != "— nenhum —" and not cartoes.empty:
                    cartao_id = int(cartoes.loc[cartoes["nome"] == cartao_nome, "id"].iloc[0])
                finance_service.criar_despesa(
                    descricao=descricao,
                    valor=valor,
                    data_vencimento=venc,
                    categoria=categoria,
                    status="Pendente",
                    usuario_id=id_do_usuario(responsavel),
                    cartao_id=cartao_id,
                    criar_lembrete_agenda=agenda,
                )
                st.success("Conta lançada.")
                st.rerun()
