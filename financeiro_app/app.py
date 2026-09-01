"""
Controle Financeiro Compartilhado + Precificacao de Estoque
==========================================================
App Streamlit multiusuario (3 pessoas, tempo quase real via auto-refresh +
replicacao do Supabase) com 4 modulos:

  1. Captura multi-fotos e ingestao inteligente (OCR / Gemini)
  2. Calendario financeiro e alertas de fluxo de caixa
  3. Painel de precificacao e historico de compras
  4. Dashboard multiusuario (divisao por pessoa)

Ponto de entrada. Rode com:  streamlit run app.py
"""
from __future__ import annotations

import streamlit as st
from streamlit_autorefresh import st_autorefresh

import config
from serviços import finance_service
from serviços.usuarios_service import listar_usuarios
from utilitários.calculations import mes_atual_str

from módulos import calendario, captura, configuracoes, multiusuario, precificacao

st.set_page_config(
    page_title="Financeiro Compartilhado",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CSS: banner de Red Alert piscante + ajustes responsivos ---------------
st.markdown(
    """
    <style>
      @keyframes piscar { 0%,100% {opacity:1;} 50% {opacity:.35;} }
      .red-alert {
          background:#c0392b; color:#fff; font-weight:700; text-align:center;
          padding:14px 18px; border-radius:10px; margin-bottom:14px;
          animation: piscar 1s infinite; font-size:1.05rem;
      }
      @media (max-width: 640px) {
          .block-container { padding-left:.6rem; padding-right:.6rem; }
      }
      [data-testid="stMetricValue"] { font-size:1.35rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _checar_config() -> bool:
    faltando = config.validar()
    if faltando:
        st.error(
            "Configuração incompleta. Defina nos **secrets** do Streamlit: "
            + ", ".join(f"`{f}`" for f in faltando)
        )
        st.stop()
    return True


def _sidebar() -> tuple[str, str]:
    with st.sidebar:
        st.title("💸 Financeiro")

        # MODULO 4.1 - Filtro de input: quem e o usuario ativo
        nomes = [u["nome"] for u in listar_usuarios()]
        usuario_ativo = st.selectbox(
            "👤 Usuário ativo (lançamentos)",
            nomes or config.USUARIOS_PADRAO,
            key="usuario_ativo",
            help="Todo lançamento/edição será atribuído a esta pessoa.",
        )

        st.divider()
        pagina = st.radio(
            "Navegação",
            [
                "🗓️ Calendário (Home)",
                "📷 Captura de Cupom",
                "📊 Precificação",
                "👥 Dashboard por Pessoa",
                "🛠️ Configurações",
            ],
            label_visibility="collapsed",
        )

        st.divider()
        st.caption("🔄 Atualização automática (tempo real)")
        if st.toggle("Ativar", value=True, key="auto_refresh"):
            st_autorefresh(
                interval=config.AUTO_REFRESH_SEGUNDOS * 1000, key="tick_refresh"
            )
        if st.button("Atualizar agora"):
            st.cache_data.clear()
            st.rerun()

    return usuario_ativo, pagina


def _banner_red_alert() -> None:
    """MODULO 2.4 - Red Alert: banner vermelho piscante se estourar o teto."""
    try:
        info = finance_service.verificar_estouro_orcamento(mes_atual_str())
    except Exception:
        return
    if info["estourou"]:
        st.markdown(
            f'<div class="red-alert">🚨 ORÇAMENTO ESTOURADO — '
            f'Gasto do mês R$ {info["gasto"]:,.2f} de um teto de R$ {info["teto"]:,.2f} '
            f'({info["percentual"]:.0f}%) 🚨</div>',
            unsafe_allow_html=True,
        )
    elif info["teto"] and info["percentual"] >= 85:
        st.warning(
            f"Atenção: já usou {info['percentual']:.0f}% do orçamento do mês "
            f"(R$ {info['gasto']:,.2f} / R$ {info['teto']:,.2f})."
        )


def main() -> None:
    _checar_config()
    usuario_ativo, pagina = _sidebar()
    _banner_red_alert()

    if pagina.startswith("🗓️"):
        calendario.render(usuario_ativo)
    elif pagina.startswith("📷"):
        captura.render(usuario_ativo)
    elif pagina.startswith("📊"):
        precificacao.render(usuario_ativo)
    elif pagina.startswith("👥"):
        multiusuario.render(usuario_ativo)
    elif pagina.startswith("🛠️"):
        configuracoes.render(usuario_ativo)


if __name__ == "__main__":
    main()
