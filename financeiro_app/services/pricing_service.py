"""MODULO 3 - Precificacao e historico de compras (padrao Assai).

- Grava notas + itens vindos do OCR.
- Le itens de uma nota como DataFrame para o st.data_editor.
- Salva a coluna 'Preco Venda' e alimenta a memoria de preco por EAN.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from db.supabase_client import get_client


# ===========================================================================
#  GRAVACAO (chamada pelo Modulo 1 apos o OCR)
# ===========================================================================
def criar_nota_com_itens(
    dados_globais: dict,
    itens: list[dict],
    usuario_id: int | None = None,
    raw_json: dict | None = None,
) -> int:
    """Cria a nota fiscal e todos os itens. Retorna o id da nota."""
    sb = get_client()
    nota = {
        "estabelecimento": dados_globais.get("estabelecimento"),
        "valor_total": float(dados_globais.get("valor_total") or 0),
        "data_emissao": dados_globais.get("data_emissao"),
        "forma_pagamento": dados_globais.get("forma_pagamento"),
        "usuario_id": usuario_id,
        "raw_json": raw_json,
    }
    nota_id = (sb.table("notas_fiscais").insert(nota).execute().data or [{}])[0]["id"]

    sugeridos = memoria_precos_por_ean([i.get("codigo_ean") for i in itens])
    linhas = []
    for it in itens:
        ean = (it.get("codigo_ean") or "").strip()
        linhas.append(
            {
                "nota_id": nota_id,
                "codigo_ean": ean,
                "descricao": it.get("descricao"),
                "quantidade": float(it.get("quantidade") or 0),
                "custo_unitario": float(it.get("custo_unitario") or 0),
                # Memoria de preco: ja vem preenchido se conhecemos o EAN.
                "preco_venda": float(sugeridos.get(ean, 0.0)),
            }
        )
    if linhas:
        sb.table("itens_nota").insert(linhas).execute()

    _limpar_cache()
    return nota_id


# ===========================================================================
#  LEITURA
# ===========================================================================
@st.cache_data(ttl=20, show_spinner=False)
def listar_notas() -> pd.DataFrame:
    sb = get_client()
    dados = (
        sb.table("notas_fiscais")
        .select("*, usuarios(nome)")
        .order("criado_em", desc=True)
        .execute()
        .data
        or []
    )
    df = pd.json_normalize(dados)
    if not df.empty:
        df["usuario_nome"] = df.get("usuarios.nome")
        df["valor_total"] = pd.to_numeric(df["valor_total"], errors="coerce").fillna(0.0)
    return df


@st.cache_data(ttl=10, show_spinner=False)
def itens_da_nota(nota_id: int) -> pd.DataFrame:
    sb = get_client()
    dados = (
        sb.table("itens_nota")
        .select("*")
        .eq("nota_id", nota_id)
        .order("id")
        .execute()
        .data
        or []
    )
    df = pd.DataFrame(dados)
    if df.empty:
        return pd.DataFrame(
            columns=["id", "codigo_ean", "descricao", "quantidade", "custo_unitario", "preco_venda"]
        )
    for c in ["quantidade", "custo_unitario", "preco_venda"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    return df


# ===========================================================================
#  MEMORIA DE PRECO (sugestao automatica por EAN)
# ===========================================================================
@st.cache_data(ttl=60, show_spinner=False)
def memoria_precos_por_ean(eans: list[str]) -> dict[str, float]:
    eans = [e for e in {(e or "").strip() for e in eans} if e]
    if not eans:
        return {}
    sb = get_client()
    dados = (
        sb.table("memoria_preco")
        .select("codigo_ean, preco_venda_sugerido")
        .in_("codigo_ean", eans)
        .execute()
        .data
        or []
    )
    return {d["codigo_ean"]: float(d["preco_venda_sugerido"]) for d in dados}


def salvar_precos_da_nota(nota_id: int, df_editado: pd.DataFrame) -> None:
    """Persiste a coluna 'preco_venda' de cada item e atualiza a memoria de preco."""
    sb = get_client()
    memoria = []
    for _, linha in df_editado.iterrows():
        preco = float(linha.get("preco_venda") or 0)
        custo = float(linha.get("custo_unitario") or 0)
        sb.table("itens_nota").update({"preco_venda": preco}).eq("id", int(linha["id"])).execute()

        ean = (linha.get("codigo_ean") or "").strip()
        if ean and preco > 0:
            margem = ((preco - custo) / preco * 100) if preco else 0.0
            memoria.append(
                {
                    "codigo_ean": ean,
                    "descricao": linha.get("descricao"),
                    "preco_venda_sugerido": round(preco, 4),
                    "margem_pct": round(margem, 2),
                    "atualizado_em": datetime.utcnow().isoformat(),
                }
            )
    if memoria:
        sb.table("memoria_preco").upsert(memoria, on_conflict="codigo_ean").execute()
    _limpar_cache()


def _limpar_cache() -> None:
    for fn in (listar_notas, itens_da_nota, memoria_precos_por_ean):
        try:
            fn.clear()
        except Exception:
            pass
