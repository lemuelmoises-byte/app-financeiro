-- ============================================================================
--  ESQUEMA DO BANCO (Supabase / PostgreSQL)
--  Rode este script no SQL Editor do Supabase antes de subir o app.
-- ============================================================================

-- ---------- Usuarios (as 3 pessoas que compartilham o controle) --------------
create table if not exists usuarios (
    id          bigint generated always as identity primary key,
    nome        text not null unique,
    criado_em   timestamptz not null default now()
);

insert into usuarios (nome)
values ('Usuário 1'), ('Usuário 2'), ('Usuário 3')
on conflict (nome) do nothing;

-- ---------- Cartoes de credito ---------------------------------------------
create table if not exists cartoes (
    id                 bigint generated always as identity primary key,
    nome               text not null,               -- ex: "Cartão Inter"
    bandeira           text,
    limite_total       numeric(12,2) not null default 0,
    limite_disponivel  numeric(12,2) not null default 0,
    dia_fechamento     int not null check (dia_fechamento between 1 and 31),
    dia_vencimento     int not null check (dia_vencimento between 1 and 31),
    criado_em          timestamptz not null default now()
);

-- ---------- Notas fiscais / cupons ----------------------------------------
create table if not exists notas_fiscais (
    id               bigint generated always as identity primary key,
    estabelecimento  text,
    valor_total      numeric(12,2) not null default 0,
    data_emissao     date,
    forma_pagamento  text,
    usuario_id       bigint references usuarios(id),
    raw_json         jsonb,                          -- resposta bruta do OCR
    criado_em        timestamptz not null default now()
);

-- ---------- Itens de cada nota -------------------------------------------
create table if not exists itens_nota (
    id              bigint generated always as identity primary key,
    nota_id         bigint not null references notas_fiscais(id) on delete cascade,
    codigo_ean      text,
    descricao       text,
    quantidade      numeric(12,3) not null default 0,
    custo_unitario  numeric(12,4) not null default 0,   -- CUSTO LIQUIDO (ja com desconto)
    preco_venda     numeric(12,4) not null default 0,
    criado_em       timestamptz not null default now()
);
create index if not exists idx_itens_nota_nota on itens_nota(nota_id);
create index if not exists idx_itens_nota_ean  on itens_nota(codigo_ean);

-- ---------- Memoria de preco (sugestao automatica por EAN) ---------------
create table if not exists memoria_preco (
    codigo_ean            text primary key,
    descricao             text,
    preco_venda_sugerido  numeric(12,4) not null default 0,
    margem_pct            numeric(6,2) not null default 0,
    atualizado_em         timestamptz not null default now()
);

-- ---------- Despesas / contas a pagar (fluxo de caixa) ------------------
create table if not exists despesas (
    id                bigint generated always as identity primary key,
    descricao         text not null,
    categoria         text not null default 'Geral',
    valor             numeric(12,2) not null default 0,
    data_vencimento   date not null,
    status            text not null default 'Pendente' check (status in ('Pendente','Pago')),
    pago_em           timestamptz,
    usuario_id        bigint references usuarios(id),
    cartao_id         bigint references cartoes(id),
    nota_id           bigint references notas_fiscais(id) on delete set null,
    google_event_id   text,
    criado_em         timestamptz not null default now()
);
create index if not exists idx_despesas_venc   on despesas(data_vencimento);
create index if not exists idx_despesas_status on despesas(status);

-- ---------- Orcamento mensal (teto de gastos) --------------------------
create table if not exists orcamento (
    mes    text primary key,           -- formato 'AAAA-MM'
    teto   numeric(12,2) not null default 0
);

-- ============================================================================
--  TEMPO REAL: habilite a replicacao para as tabelas compartilhadas
--  (Supabase -> Database -> Replication, ou via SQL abaixo)
-- ============================================================================
alter publication supabase_realtime add table despesas;
alter publication supabase_realtime add table notas_fiscais;
alter publication supabase_realtime add table itens_nota;
alter publication supabase_realtime add table cartoes;

-- ============================================================================
--  RLS: para uso interno entre 3 pessoas de confianca, o mais simples e
--  DESABILITAR RLS (as tabelas ficam acessiveis com a chave anon).
--  Se preferir travar, habilite e crie policies de acordo com o seu login.
-- ============================================================================
-- alter table despesas enable row level security;
-- create policy "acesso total interno" on despesas for all using (true) with check (true);
