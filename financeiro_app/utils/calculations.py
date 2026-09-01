"""Funcoes puras de calculo (sem I/O). Faceis de testar isoladamente."""
from __future__ import annotations

import calendar as _calendar
from datetime import date, timedelta

import pandas as pd

# Colunas que o usuario NAO pode editar no painel de precificacao.
COLUNAS_TRAVADAS = ["codigo_ean", "descricao", "quantidade", "custo_unitario"]
COLUNA_EDITAVEL = "preco_venda"


def calcular_precificacao(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica, linha a linha, Lucro Unidade e Margem % via pandas (vetorizado)."""
    df = df.copy()
    for col in ["quantidade", "custo_unitario", "preco_venda"]:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["lucro_unidade"] = df["preco_venda"] - df["custo_unitario"]
    df["margem_pct"] = 0.0
    mask = df["preco_venda"] != 0
    df.loc[mask, "margem_pct"] = (
        df.loc[mask, "lucro_unidade"] / df.loc[mask, "preco_venda"] * 100
    ).round(2)
    df["lucro_unidade"] = df["lucro_unidade"].round(2)
    return df


def metricas_consolidadas(df: pd.DataFrame) -> dict:
    """Totais do rodape do painel de precificacao."""
    df = calcular_precificacao(df)
    custo_total = float((df["custo_unitario"] * df["quantidade"]).sum())
    faturamento = float((df["preco_venda"] * df["quantidade"]).sum())
    lucro_bruto = faturamento - custo_total
    margem_media = (lucro_bruto / faturamento * 100) if faturamento else 0.0
    return {
        "custo_total": round(custo_total, 2),
        "faturamento_projetado": round(faturamento, 2),
        "lucro_bruto_projetado": round(lucro_bruto, 2),
        "margem_media_bruta": round(margem_media, 2),
    }


def _dia_valido(ano: int, mes: int, dia: int) -> date:
    """Ajusta o dia para o ultimo dia do mes quando necessario (ex: dia 31 em fev)."""
    ultimo = _calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(dia, ultimo))


def proxima_data_no_dia(dia: int, hoje: date | None = None) -> date:
    """Proxima ocorrencia de um 'dia do mes' a partir de hoje (inclusive)."""
    hoje = hoje or date.today()
    candidato = _dia_valido(hoje.year, hoje.month, dia)
    if candidato < hoje:
        ano = hoje.year + (1 if hoje.month == 12 else 0)
        mes = 1 if hoje.month == 12 else hoje.month + 1
        candidato = _dia_valido(ano, mes, dia)
    return candidato


def melhor_dia_compra(dia_fechamento: int, hoje: date | None = None) -> date:
    """Melhor dia de compra = logo apos o fechamento da fatura.

    Comprar 1 dia depois do fechamento joga a despesa para a fatura seguinte,
    maximizando o prazo ate o pagamento.
    """
    hoje = hoje or date.today()
    return proxima_data_no_dia((dia_fechamento % 28) + 1, hoje)


def mes_atual_str(hoje: date | None = None) -> str:
    hoje = hoje or date.today()
    return hoje.strftime("%Y-%m")


def intervalo_do_mes(mes: str) -> tuple[date, date]:
    """Retorna (primeiro_dia, primeiro_dia_do_mes_seguinte) para filtros SQL."""
    ano, mes_n = map(int, mes.split("-"))
    inicio = date(ano, mes_n, 1)
    if mes_n == 12:
        fim = date(ano + 1, 1, 1)
    else:
        fim = date(ano, mes_n + 1, 1)
    return inicio, fim
