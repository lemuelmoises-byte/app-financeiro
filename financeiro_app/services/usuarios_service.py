"""MODULO 4 - Cadastro/consulta das 3 pessoas."""
from __future__ import annotations

import streamlit as st

from config import USUARIOS_PADRAO
from db.supabase_client import get_client


@st.cache_data(ttl=300, show_spinner=False)
def listar_usuarios() -> list[dict]:
    sb = get_client()
    resp = sb.table("usuarios").select("*").order("id").execute()
    dados = resp.data or []
    if not dados:  # semente automatica se a tabela estiver vazia
        for nome in USUARIOS_PADRAO:
            sb.table("usuarios").upsert({"nome": nome}, on_conflict="nome").execute()
        resp = sb.table("usuarios").select("*").order("id").execute()
        dados = resp.data or []
    return dados


def mapa_nome_para_id() -> dict[str, int]:
    return {u["nome"]: u["id"] for u in listar_usuarios()}


def id_do_usuario(nome: str) -> int | None:
    return mapa_nome_para_id().get(nome)
