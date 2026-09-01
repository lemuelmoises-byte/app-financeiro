"""Fabrica do cliente Supabase (com cache de recurso do Streamlit)."""
from __future__ import annotations

import streamlit as st
from supabase import Client, create_client

from config import SUPABASE_KEY, SUPABASE_URL


@st.cache_resource(show_spinner=False)
def get_client() -> Client:
    """Retorna um unico cliente Supabase reutilizado por toda a sessao."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            "Supabase nao configurado. Defina SUPABASE_URL e SUPABASE_KEY nos secrets."
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)
