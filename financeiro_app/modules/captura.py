"""MODULO 1 (UI) - Captura multi-fotos e ingestao inteligente (OCR)."""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import streamlit as st

from services import finance_service, ocr_service, pricing_service
from services.usuarios_service import id_do_usuario


def _parse_data(txt: str | None) -> date:
    if not txt:
        return date.today()
    try:
        return datetime.strptime(txt[:10], "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def render(usuario_ativo: str) -> None:
    st.header("📷 Captura de Cupom — Upload em Lote + OCR")
    st.caption(
        "Envie **4 ou mais fotos** em sequência de um único cupom longo "
        "(ex: Assaí). O Gemini consolida tudo em um só documento."
    )

    arquivos = st.file_uploader(
        "Fotos do cupom fiscal",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        help="As imagens devem ser partes sequenciais do MESMO cupom.",
    )

    if arquivos:
        st.image(arquivos, width=140, caption=[f"Foto {i+1}" for i in range(len(arquivos))])

    if st.button("🔎 Processar lote com o Gemini", type="primary", disabled=not arquivos):
        with st.spinner(f"Consolidando {len(arquivos)} imagens..."):
            try:
                st.session_state["ocr_resultado"] = ocr_service.processar_lote(arquivos)
            except Exception as exc:
                st.error(f"Falha no OCR: {exc}")
                return

    resultado = st.session_state.get("ocr_resultado")
    if not resultado:
        return

    st.divider()
    _tela_conferencia(resultado, usuario_ativo)


def _tela_conferencia(resultado: dict, usuario_ativo: str) -> None:
    g = resultado["dados_globais"]
    itens = resultado["itens"]

    st.subheader("1) Dados globais → Financeiro / Calendário")
    c1, c2, c3 = st.columns(3)
    estabelecimento = c1.text_input("Estabelecimento", g.get("estabelecimento", ""))
    valor_total = c2.number_input(
        "Valor total (R$)", min_value=0.0, value=float(g.get("valor_total") or 0), step=0.01
    )
    data_emissao = c3.date_input("Data de emissão", _parse_data(g.get("data_emissao")))

    c4, c5, c6 = st.columns(3)
    forma_pagamento = c4.selectbox(
        "Forma de pagamento",
        ["PIX", "Cartão", "Dinheiro", "Outro"],
        index=["PIX", "Cartão", "Dinheiro", "Outro"].index(g.get("forma_pagamento", "Outro"))
        if g.get("forma_pagamento") in ["PIX", "Cartão", "Dinheiro", "Outro"]
        else 3,
    )
    status_fin = c5.selectbox("Status financeiro", ["Pago", "Pendente"])
    vencimento = c6.date_input(
        "Vencimento (se pendente)", max(data_emissao, date.today())
    )
    categoria = st.text_input("Categoria da despesa", "Compras / Estoque")

    st.subheader("2) Itens → Precificação")
    df_itens = pd.DataFrame(itens)
    st.dataframe(df_itens, use_container_width=True, hide_index=True)
    st.caption(
        f"{len(itens)} itens · custo unitário já **líquido de descontos** "
        "(regra aplicada pelo OCR)."
    )

    if st.button("💾 Confirmar e distribuir (Duplo Destino)", type="primary"):
        uid = id_do_usuario(usuario_ativo)
        dados_globais = {
            "estabelecimento": estabelecimento,
            "valor_total": valor_total,
            "data_emissao": data_emissao.isoformat(),
            "forma_pagamento": forma_pagamento,
        }

        # Destino A: Precificacao (nota + itens)
        nota_id = pricing_service.criar_nota_com_itens(
            dados_globais, itens, usuario_id=uid, raw_json=resultado
        )

        # Destino B: Financeiro / Calendario (despesa do valor total)
        finance_service.criar_despesa(
            descricao=f"Compra {estabelecimento}".strip(),
            valor=valor_total,
            data_vencimento=vencimento if status_fin == "Pendente" else data_emissao,
            categoria=categoria,
            status=status_fin,
            usuario_id=uid,
            nota_id=nota_id,
            criar_lembrete_agenda=(status_fin == "Pendente"),
        )

        st.session_state.pop("ocr_resultado", None)
        st.success(
            f"Nota #{nota_id} enviada à Precificação e despesa criada no Fluxo de Caixa."
        )
        st.balloons()
