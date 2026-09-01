"""MODULO 2.5 - Integracao com o Google Calendar.

Sempre que uma conta pendente futura e salva, criamos um lembrete na agenda
configurada, com notificacao 1 dia antes (aparece no celular do usuario).

Autenticacao: conta de servico do Google (Service Account). Compartilhe o
calendario alvo com o e-mail da conta de servico e informe o GOOGLE_CALENDAR_ID.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta

import streamlit as st

from config import GOOGLE_CALENDAR_ID, TIMEZONE, google_service_account_info

_ESCOPOS = ["https://www.googleapis.com/auth/calendar.events"]
LEMBRETE_MINUTOS_ANTES = 24 * 60  # 1 dia antes


@st.cache_resource(show_spinner=False)
def _servico():
    """Constroi (e cacheia) o cliente da API do Google Calendar."""
    info = google_service_account_info()
    if not info:
        return None
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    cred = service_account.Credentials.from_service_account_info(info, scopes=_ESCOPOS)
    return build("calendar", "v3", credentials=cred, cache_discovery=False)


def integrar_google_agenda(
    titulo: str,
    data_vencimento,
    valor: float,
    descricao: str = "",
) -> str | None:
    """Cria um evento de lembrete e retorna o ID do evento (ou None se desligado).

    O evento e um "all-day-ish" as 09:00 do dia do vencimento, com um lembrete
    popup 1 dia antes.
    """
    servico = _servico()
    if servico is None:
        return None

    if isinstance(data_vencimento, str):
        data_vencimento = datetime.strptime(data_vencimento[:10], "%Y-%m-%d").date()

    inicio = datetime.combine(data_vencimento, time(9, 0))
    fim = inicio + timedelta(hours=1)

    evento = {
        "summary": f"💰 {titulo} — R$ {valor:,.2f}",
        "description": descricao or "Lançamento do app de controle financeiro compartilhado.",
        "start": {"dateTime": inicio.isoformat(), "timeZone": TIMEZONE},
        "end": {"dateTime": fim.isoformat(), "timeZone": TIMEZONE},
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": LEMBRETE_MINUTOS_ANTES},
                {"method": "email", "minutes": LEMBRETE_MINUTOS_ANTES},
            ],
        },
    }

    criado = (
        servico.events()
        .insert(calendarId=GOOGLE_CALENDAR_ID, body=evento)
        .execute()
    )
    return criado.get("id")


def remover_lembrete(event_id: str) -> None:
    """Remove o lembrete da agenda (usado ao dar baixa/excluir a despesa)."""
    servico = _servico()
    if servico is None or not event_id:
        return
    try:
        servico.events().delete(calendarId=GOOGLE_CALENDAR_ID, eventId=event_id).execute()
    except Exception:
        pass
