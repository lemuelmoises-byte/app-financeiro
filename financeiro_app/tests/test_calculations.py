"""Testes das funcoes puras de calculo.  Rode:  pytest -q"""
from datetime import date

import pandas as pd

from utils.calculations import (
    calcular_precificacao,
    melhor_dia_compra,
    metricas_consolidadas,
    proxima_data_no_dia,
)


def _df():
    return pd.DataFrame(
        [
            {"codigo_ean": "1", "descricao": "Arroz", "quantidade": 2, "custo_unitario": 20.0, "preco_venda": 25.0},
            {"codigo_ean": "2", "descricao": "Feijao", "quantidade": 1, "custo_unitario": 8.0, "preco_venda": 10.0},
        ]
    )


def test_lucro_e_margem():
    df = calcular_precificacao(_df())
    assert df.loc[0, "lucro_unidade"] == 5.0
    assert round(df.loc[0, "margem_pct"], 2) == 20.0


def test_margem_zero_quando_preco_zero():
    df = _df()
    df.loc[0, "preco_venda"] = 0
    out = calcular_precificacao(df)
    assert out.loc[0, "margem_pct"] == 0.0


def test_metricas_consolidadas():
    m = metricas_consolidadas(_df())
    assert m["custo_total"] == 48.0          # 2*20 + 1*8
    assert m["faturamento_projetado"] == 60.0  # 2*25 + 1*10
    assert m["lucro_bruto_projetado"] == 12.0
    assert round(m["margem_media_bruta"], 2) == 20.0


def test_proxima_data_no_dia_rola_para_o_mes_seguinte():
    hoje = date(2026, 3, 20)
    assert proxima_data_no_dia(10, hoje) == date(2026, 4, 10)
    assert proxima_data_no_dia(25, hoje) == date(2026, 3, 25)


def test_melhor_dia_compra_e_apos_o_fechamento():
    hoje = date(2026, 3, 1)
    assert melhor_dia_compra(20, hoje) == date(2026, 3, 21)
