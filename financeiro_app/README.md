# 💸 Controle Financeiro Compartilhado + Precificação de Estoque

App **Streamlit + Supabase (PostgreSQL)** para 3 pessoas compartilharem, em tempo
quase real, o controle de fluxo de caixa e a precificação de estoque a partir de
fotos de cupons fiscais longos (padrão Assaí / Atacadão).

## Módulos

| Módulo | Arquivo | O que faz |
|---|---|---|
| 1 · Captura + OCR | [`modules/captura.py`](modules/captura.py) · [`services/ocr_service.py`](services/ocr_service.py) | Upload em lote (`st.file_uploader`, `accept_multiple_files=True`), consolida 4+ fotos de **um único cupom** via Gemini `gemini-2.5-flash`, devolve JSON padronizado com **custo unitário líquido de descontos**. Duplo destino: dados globais → financeiro/calendário, itens → precificação. |
| 2 · Calendário financeiro | [`modules/calendario.py`](modules/calendario.py) · [`services/finance_service.py`](services/finance_service.py) | `streamlit-calendar` na Home com somatório de despesas pendentes por dia; modal por clique com contas linha a linha e botão **Dar Baixa** (1 clique → `Pendente`→`Pago`); indicador de cartões com **Melhor Dia de Compra**; **Red Alert** piscante ao estourar o teto; `integrar_google_agenda` cria lembrete 1 dia antes. |
| 3 · Precificação | [`modules/precificacao.py`](modules/precificacao.py) · [`services/pricing_service.py`](services/pricing_service.py) | Histórico de notas; `st.data_editor` com **EAN/Descrição/Qtd/Custo travados** e só **Preço Venda** editável; `Lucro Unidade` e `Margem %` recalculados em tempo real com Pandas; `st.metric` no rodapé; **Memória de Preço** por EAN no Supabase. |
| 4 · Multiusuário | [`modules/multiusuario.py`](modules/multiusuario.py) | Drop-down de usuário ativo na barra lateral; gráfico de pizza por categoria + barras de **Gastos por Pessoa** no mês. |

## Estrutura

```
financeiro_app/
├── app.py                     # entrypoint, sidebar, Red Alert, auto-refresh
├── config.py                  # segredos (st.secrets / env)
├── requirements.txt
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example   # modelo — copie para secrets.toml
├── db/
│   ├── schema.sql             # DDL + replicação (rode no Supabase)
│   └── supabase_client.py
├── services/                  # regras de negócio + acesso a dados
│   ├── ocr_service.py
│   ├── finance_service.py
│   ├── pricing_service.py
│   ├── google_calendar.py
│   └── usuarios_service.py
├── modules/                   # uma UI por módulo
│   ├── captura.py
│   ├── calendario.py
│   ├── precificacao.py
│   ├── multiusuario.py
│   └── configuracoes.py
├── utils/calculations.py      # funções puras (testáveis)
└── tests/test_calculations.py
```

## Rodando localmente

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # preencha as chaves
streamlit run app.py
```

Testes: `pytest -q`

## Passo a passo — deploy grátis no Streamlit Community Cloud

1. **Supabase**
   - Crie um projeto em <https://supabase.com> (plano free).
   - Em **SQL Editor**, cole e rode [`db/schema.sql`](db/schema.sql). Isso cria as
     tabelas, os índices, semeia os 3 usuários e habilita a replicação em tempo
     real (`supabase_realtime`).
   - Em **Project Settings → API**, copie `Project URL` e a chave `anon`
     (ou `service_role` se preferir acesso total sem RLS).

2. **Gemini**
   - Gere uma API key em <https://aistudio.google.com/app/apikey>.

3. **Google Calendar (opcional — só se quiser os lembretes)**
   - No Google Cloud Console: ative a **Google Calendar API**, crie uma
     **Service Account**, gere uma chave JSON.
   - No Google Calendar, compartilhe o calendário desejado com o
     `client_email` da service account (permissão "Fazer alterações em eventos").

4. **GitHub**
   - Suba a pasta `financeiro_app/` para um repositório (o `.gitignore` já
     protege `secrets.toml`).

5. **Streamlit Cloud**
   - Acesse <https://share.streamlit.io> → **New app** → escolha o repositório,
     branch e `app.py` como *Main file path*.
   - Em **Advanced settings → Secrets**, cole o conteúdo do seu
     `secrets.toml` (mesmo formato do `.example`).
   - **Deploy**. Atualizações no `main` reimplantam sozinhas.

### Variáveis de ambiente / secrets

| Chave | Obrigatória | Descrição |
|---|---|---|
| `SUPABASE_URL` | ✅ | URL do projeto Supabase |
| `SUPABASE_KEY` | ✅ | Chave `anon` ou `service_role` |
| `GEMINI_API_KEY` | ✅ | Chave da API do Gemini |
| `GEMINI_MODEL` | ➖ | Default `gemini-2.5-flash` |
| `TIMEZONE` | ➖ | Default `America/Sao_Paulo` |
| `AUTO_REFRESH_SEGUNDOS` | ➖ | Intervalo do refresh automático (default 30) |
| `GOOGLE_CALENDAR_ID` | ➖ | E-mail do calendário alvo ou `primary` |
| `[gcp_service_account]` | ➖ | Tabela TOML com o JSON da service account |

> As chaves ficam **somente** nos Secrets do Streamlit — nunca no código nem no
> repositório. `config.py` lê de `st.secrets` e, como fallback, de variáveis de
> ambiente.

## Notas de "tempo real"

O Streamlit não mantém websocket com o Supabase no cliente. A sincronização
entre as 3 pessoas é feita por **auto-refresh** (`streamlit-autorefresh`, ligável
na barra lateral) + caches curtos (`ttl` de 10–30 s) nas leituras. A replicação
`supabase_realtime` já fica habilitada para evoluções futuras (ex: worker de push).
