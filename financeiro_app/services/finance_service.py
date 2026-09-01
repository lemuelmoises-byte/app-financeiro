"""MODULO 2 - Fluxo de caixa: despesas, cartoes, orcamento e calendario.

Camada de acesso a dados (repositorio) + regras de negocio do financeiro.
"""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import streamlit as st

from db.supabase_client import get_client
from services.google_calendar import integrar_google_agenda, remover_lembrete
from utils.calculations import (
    intervalo_do_mes,
    melhor_dia_compra,
    mes_atual_str,
    proxima_data_no_dia,
)


# ===========================================================================
#  DESPESAS
# ===========================================================================
def criar_despesa(
    descricao: str,
    valor: float,
    data_vencimento: date,
    categoria: str = "Geral",
    status: str = "Pendente",
    usuario_id: int | None = None,
    cartao_id: int | None = None,
    nota_id: int | None = None,
    criar_lembrete_agenda: bool = True,
) -> dict:
    """Insere uma despesa. Se for futura e pendente, cria lembrete no Google Calendar."""
    sb = get_client()
    registro = {
        "descricao": descricao,
        "valor": round(float(valor), 2),
        "data_vencimento": data_vencimento.isoformat(),
        "categoria": categoria,
        "status": status,
        "usuario_id": usuario_id,
        "cartao_id": cartao_id,
        "nota_id": nota_id,
    }

    event_id = None
    if criar_lembrete_agenda and status == "Pendente" and data_vencimento >= date.today():
        try:
            event_id = integrar_google_agenda(descricao, data_vencimento, valor, categoria)
        except Exception as exc:  # nao bloqueia o lancamento
            st.warning(f"Despesa salva, mas o lembrete no Google Agenda falhou: {exc}")
    registro["google_event_id"] = event_id

    resp = sb.table("despesas").insert(registro).execute()
    _limpar_cache()
    return (resp.data or [{}])[0]


def dar_baixa(despesa_id: int) -> None:
    """Atualiza o status de 'Pendente' para 'Pago' com 1 clique."""
    sb = get_client()
    atual = sb.table("despesas").select("*").eq("id", despesa_id).single().execute().data
    sb.table("despesas").update(
        {"status": "Pago", "pago_em": datetime.utcnow().isoformat()}
    ).eq("id", despesa_id).execute()
    if atual and atual.get("google_event_id"):
        remover_lembrete(atual["google_event_id"])
    _limpar_cache()


def excluir_despesa(despesa_id: int) -> None:
    sb = get_client()
    atual = sb.table("despesas").select("google_event_id").eq("id", despesa_id).single().execute().data
    sb.table("despesas").delete().eq("id", despesa_id).execute()
    if atual and atual.get("google_event_id"):
        remover_lembrete(atual["google_event_id"])
    _limpar_cache()


@st.cache_data(ttl=15, show_spinner=False)
def listar_despesas(
    mes: str | None = None,
    status: str | None = None,
) -> pd.DataFrame:
    sb = get_client()
    q = sb.table("despesas").select("*, usuarios(nome), cartoes(nome)")
    if mes:
        inicio, fim = intervalo_do_mes(mes)
        q = q.gte("data_vencimento", inicio.isoformat()).lt("data_vencimento", fim.isoformat())
    if status:
        q = q.eq("status", status)
    dados = q.order("data_vencimento").execute().data or []
    df = pd.json_normalize(dados)
    if not df.empty:
        df["usuario_nome"] = df.get("usuarios.nome")
        df["cartao_nome"] = df.get("cartoes.nome")
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
        df["data_vencimento"] = pd.to_datetime(df["data_vencimento"]).dt.date
    return df


def despesas_do_dia(dia: date) -> pd.DataFrame:
    df = listar_despesas()
    if df.empty:
        return df
    return df[df["data_vencimento"] == dia].copy()


# ===========================================================================
#  CALENDARIO (eventos agregados por dia)
# ===========================================================================
def eventos_calendario(apenas_pendentes: bool = True) -> list[dict]:
    """Um evento por dia com o SOMATORIO de despesas (compacto no quadradinho)."""
    df = listar_despesas(status="Pendente" if apenas_pendentes else None)
    if df.empty:
        return []
    agrupado = df.groupby("data_vencimento")["valor"].agg(["sum", "count"]).reset_index()
    eventos = []
    for _, linha in agrupado.iterrows():
        total = float(linha["sum"])
        eventos.append(
            {
                "title": f"R$ {total:,.2f} ({int(linha['count'])})",
                "start": linha["data_vencimento"].isoformat(),
                "allDay": True,
                "color": "#c0392b" if total >= 500 else "#e67e22",
            }
        )
    return eventos


# ===========================================================================
#  CARTOES
# ===========================================================================
@st.cache_data(ttl=60, show_spinner=False)
def listar_cartoes() -> pd.DataFrame:
    sb = get_client()
    dados = sb.table("cartoes").select("*").order("nome").execute().data or []
    return pd.DataFrame(dados)


def salvar_cartao(dados: dict, cartao_id: int | None = None) -> None:
    sb = get_client()
    if cartao_id:
        sb.table("cartoes").update(dados).eq("id", cartao_id).execute()
    else:
        sb.table("cartoes").insert(dados).execute()
    _limpar_cache()


def resumo_cartoes() -> list[dict]:
    """Para cada cartao: limite disponivel + 'melhor dia de compra'."""
    df = listar_cartoes()
    resumo = []
    for _, c in df.iterrows():
        resumo.append(
            {
                "id": int(c["id"]),
                "nome": c["nome"],
                "limite_total": float(c.get("limite_total") or 0),
                "limite_disponivel": float(c.get("limite_disponivel") or 0),
                "dia_fechamento": int(c["dia_fechamento"]),
                "dia_vencimento": int(c["dia_vencimento"]),
                "proximo_fechamento": proxima_data_no_dia(int(c["dia_fechamento"])),
                "melhor_dia_compra": melhor_dia_compra(int(c["dia_fechamento"])),
            }
        )
    return resumo


# ===========================================================================
#  ORCAMENTO / RED ALERTS
# ===========================================================================
@st.cache_data(ttl=30, show_spinner=False)
def get_teto(mes: str | None = None) -> float:
    sb = get_client()
    mes = mes or mes_atual_str()
    dado = sb.table("orcamento").select("teto").eq("mes", mes).execute().data
    return float(dado[0]["teto"]) if dado else 0.0


def set_teto(valor: float, mes: str | None = None) -> None:
    sb = get_client()
    mes = mes or mes_atual_str()
    sb.table("orcamento").upsert({"mes": mes, "teto": round(float(valor), 2)}).execute()
    _limpar_cache()


def total_gasto_mes(mes: str | None = None) -> float:
    mes = mes or mes_atual_str()
    df = listar_despesas(mes=mes)
    return float(df["valor"].sum()) if not df.empty else 0.0


def verificar_estouro_orcamento(mes: str | None = None) -> dict:
    """Retorna dados para o banner de Red Alert."""
    mes = mes or mes_atual_str()
    teto = get_teto(mes)
    gasto = total_gasto_mes(mes)
    return {
        "mes": mes,
        "teto": teto,
        "gasto": gasto,
        "estourou": teto > 0 and gasto > teto,
        "percentual": (gasto / teto * 100) if teto else 0.0,
    }


# ===========================================================================
#  GASTOS POR PESSOA (dashboard multiusuario)
# ===========================================================================
def gastos_por_pessoa(mes: str | None = None) -> pd.DataFrame:
    df = listar_despesas(mes=mes or mes_atual_str())
    if df.empty:
        return pd.DataFrame(columns=["usuario_nome", "valor"])
    return (
        df.assign(usuario_nome=df["usuario_nome"].fillna("Sem responsável"))
        .groupby("usuario_nome")["valor"]
        .sum()
        .reset_index()
        .sort_values("valor", ascending=False)
    )


def gastos_por_categoria(mes: str | None = None) -> pd.DataFrame:
    df = listar_despesas(mes=mes or mes_atual_str())
    if df.empty:
        return pd.DataFrame(columns=["categoria", "valor"])
    return df.groupby("categoria")["valor"].sum().reset_index().sort_values("valor", ascending=False)


# ===========================================================================
def _limpar_cache() -> None:
    for fn in (
        listar_despesas,
        listar_cartoes,
        get_teto,
    ):
        try:
            fn.clear()
        except Exception:
            pass
