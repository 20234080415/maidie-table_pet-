alter table public.maidie_admin_config
  add column session_secret text;

create table public.maidie_admin_runtime (
  id boolean primary key default true check (id),
  environment text not null check (environment in ('production')),
  enabled boolean not null default false,
  proxy_secret_hash text not null
    check (proxy_secret_hash ~ '^[0-9a-f]{64}$'),
  updated_at timestamptz not null default now()
);

alter table public.maidie_admin_runtime enable row level security;
revoke all on table public.maidie_admin_runtime from anon, authenticated;
grant select, insert, update, delete
  on table public.maidie_admin_runtime to service_role;
