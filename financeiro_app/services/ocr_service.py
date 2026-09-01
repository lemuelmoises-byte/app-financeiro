"""MODULO 1 - Ingestao inteligente (OCR) via Gemini.

Recebe um LOTE de fotos (varias imagens sequenciais de um unico cupom fiscal
longo, tipo Assai) e devolve um JSON consolidado e padronizado.
"""
from __future__ import annotations

import io
import json
from typing import Any

import google.generativeai as genai
from PIL import Image

from config import GEMINI_API_KEY, GEMINI_MODEL

# ---------------------------------------------------------------------------
PROMPT_CONSOLIDACAO = """Voce e um sistema de OCR fiscal especializado em cupons e notas do varejo
brasileiro (Assai, Atacadao, mercados). Voce recebera VARIAS imagens que sao
PARTES SEQUENCIAIS de um UNICO cupom fiscal longo. Trate todas as imagens como
um so documento.

REGRAS OBRIGATORIAS:
1. Consolide os itens de todas as imagens. NAO duplique linhas que aparecem
   repetidas por causa da sobreposicao entre as fotos.
2. "custo_unitario" deve ser o CUSTO LIQUIDO: subtraia descontos por item,
   promocoes "leve X pague Y" e rateie descontos globais proporcionalmente.
3. "quantidade" em unidades; use o peso em kg quando o produto for a granel.
4. Datas no formato AAAA-MM-DD. Numeros com ponto decimal, sem "R$" e sem
   separador de milhar.
5. "forma_pagamento": um de "PIX", "Cartão", "Dinheiro" ou "Outro".
6. Campo inexistente -> null (ou "" para texto).
7. Responda SOMENTE com JSON valido. Sem markdown, sem comentarios.

FORMATO EXATO DE SAIDA:
{
  "dados_globais": {
    "estabelecimento": "Nome da Loja",
    "valor_total": 0.00,
    "data_emissao": "AAAA-MM-DD",
    "forma_pagamento": "PIX/Cartão/Dinheiro"
  },
  "itens": [
    {"codigo_ean": "string", "descricao": "string", "quantidade": 0, "custo_unitario": 0.00}
  ]
}
"""


def _abrir_imagens(arquivos: list) -> list[Image.Image]:
    imagens: list[Image.Image] = []
    for arq in arquivos:
        dados = arq.read()
        try:
            arq.seek(0)
        except Exception:
            pass
        img = Image.open(io.BytesIO(dados))
        img.load()
        imagens.append(img)
    return imagens


def _num(valor: Any, casas: int = 2) -> float:
    try:
        if isinstance(valor, str):
            valor = valor.replace("R$", "").replace(".", "").replace(",", ".").strip()
        return round(float(valor), casas)
    except (TypeError, ValueError):
        return 0.0


def _normalizar(bruto: dict) -> dict:
    globais = bruto.get("dados_globais", {}) or {}
    itens_norm = []
    for item in bruto.get("itens", []) or []:
        itens_norm.append(
            {
                "codigo_ean": str(item.get("codigo_ean") or "").strip(),
                "descricao": str(item.get("descricao") or "").strip(),
                "quantidade": _num(item.get("quantidade"), 3) or 1.0,
                "custo_unitario": _num(item.get("custo_unitario"), 4),
            }
        )
    return {
        "dados_globais": {
            "estabelecimento": str(globais.get("estabelecimento") or "").strip(),
            "valor_total": _num(globais.get("valor_total")),
            "data_emissao": (globais.get("data_emissao") or None),
            "forma_pagamento": str(globais.get("forma_pagamento") or "Outro").strip(),
        },
        "itens": itens_norm,
    }


def processar_lote(arquivos: list) -> dict:
    """Envia o lote de imagens ao Gemini e retorna o dicionario ja normalizado.

    Parametros
    ----------
    arquivos: lista de objetos retornados pelo `st.file_uploader`
              (accept_multiple_files=True).
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY nao configurada nos secrets.")
    if not arquivos:
        raise ValueError("Nenhuma imagem enviada.")

    genai.configure(api_key=GEMINI_API_KEY)
    modelo = genai.GenerativeModel(GEMINI_MODEL)

    imagens = _abrir_imagens(arquivos)
    conteudo = [PROMPT_CONSOLIDACAO, *imagens]

    resposta = modelo.generate_content(
        conteudo,
        generation_config={
            "response_mime_type": "application/json",
            "temperature": 0.1,
        },
    )

    texto = (resposta.text or "").strip()
    try:
        bruto = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Gemini retornou JSON invalido: {exc}\n---\n{texto[:800]}")

    return _normalizar(bruto)
