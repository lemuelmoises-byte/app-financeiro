"""Carregamento centralizado de configuracoes e segredos.

A ordem de resolucao e:
1. `st.secrets` (usado no Streamlit Cloud / arquivo .streamlit/secrets.toml)
2. Variaveis de ambiente do sistema operacional

Nenhuma chave e escrita em disco ou em log.
"""
from __future__ import annotations

import json
import os
from typing import Any

import streamlit as st


def _secret(key: str, default: Any = None) -> Any:
    """Retorna um segredo procurando primeiro em st.secrets e depois no ambiente."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        # st.secrets lanca excecao quando nao ha arquivo de secrets configurado.
        pass
    return os.environ.get(key, default)


# --- Supabase ---------------------------------------------------------------
SUPABASE_URL: str | None = _secret("SUPABASE_URL")
# Use a chave `anon` para uso multiusuario com RLS, ou `service_role` para acesso total.
SUPABASE_KEY: str | None = _secret("SUPABASE_KEY")

# --- Gemini (OCR) ----------------------------------------------------------
GEMINI_API_KEY: str | None = _secret("GEMINI_API_KEY")
GEMINI_MODEL: str = _secret("GEMINI_MODEL", "gemini-2.5-flash")

# --- Google Calendar -----------------------------------------------------
GOOGLE_CALENDAR_ID: str = _secret("GOOGLE_CALENDAR_ID", "primary")
TIMEZONE: str = _secret("TIMEZONE", "America/Sao_Paulo")


def google_service_account_info() -> dict | None:
    """Le as credenciais da conta de servico do Google.

    Aceita tanto uma tabela TOML `[gcp_service_account]` quanto uma string JSON
    em `GOOGLE_SERVICE_ACCOUNT_JSON`.
    """
    try:
        if "gcp_service_account" in st.secrets:
            return dict(st.secrets["gcp_service_account"])
    except Exception:
        pass
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw:
        return json.loads(raw)
    return None


# --- App -----------------------------------------------------------------
USUARIOS_PADRAO = ["Usuário 1", "Usuário 2", "Usuário 3"]
AUTO_REFRESH_SEGUNDOS = int(_secret("AUTO_REFRESH_SEGUNDOS", 30))


def validar() -> list[str]:
    """Retorna a lista de configuracoes obrigatorias que estao faltando."""
    faltando = []
    if not SUPABASE_URL:
        faltando.append("SUPABASE_URL")
    if not SUPABASE_KEY:
        faltando.append("SUPABASE_KEY")
    if not GEMINI_API_KEY:
        faltando.append("GEMINI_API_KEY")
    return faltando
