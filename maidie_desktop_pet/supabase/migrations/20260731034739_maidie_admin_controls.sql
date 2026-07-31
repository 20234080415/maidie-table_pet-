alter table public.maidie_invite_codes
  add column note text not null default '';

alter table public.maidie_users
  add column invite_code_id bigint
    references public.maidie_invite_codes(id) on delete set null,
  add column status text not null default 'active'
    check (status in ('active', 'revoked')),
  add column revoked_at timestamptz;

create index maidie_users_status_idx
  on public.maidie_users(status);

create table public.maidie_admin_config (
  id boolean primary key default true check (id),
  password_hash text not null,
  password_salt text not null,
  owner_fingerprint text not null,
  configured_at timestamptz not null default now()
);

create table public.maidie_admin_login_limits (
  fingerprint text primary key,
  window_started_at timestamptz not null default now(),
  failure_count integer not null default 0
    check (failure_count >= 0),
  blocked_until timestamptz,
  updated_at timestamptz not null default now()
);

create table public.maidie_admin_audit_log (
  id bigint generated always as identity primary key,
  action text not null,
  target_type text not null default '',
  target_id text not null default '',
  detail jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.maidie_admin_config enable row level security;
alter table public.maidie_admin_login_limits enable row level security;
alter table public.maidie_admin_audit_log enable row level security;

revoke all on table public.maidie_admin_config from anon, authenticated;
revoke all on table public.maidie_admin_login_limits from anon, authenticated;
revoke all on table public.maidie_admin_audit_log from anon, authenticated;

grant select, insert, update, delete
  on table public.maidie_admin_config to service_role;
grant select, insert, update, delete
  on table public.maidie_admin_login_limits to service_role;
grant select, insert
  on table public.maidie_admin_audit_log to service_role;
grant usage, select
  on sequence public.maidie_admin_audit_log_id_seq to service_role;

create or replace function public.redeem_maidie_invite(
  p_code text,
  p_device_id text,
  p_token_hash text
)
returns table(success boolean, user_id uuid)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_invite_id bigint;
  v_user_id uuid;
begin
  if length(btrim(coalesce(p_code, ''))) < 4
     or length(btrim(coalesce(p_code, ''))) > 64
     or length(btrim(coalesce(p_device_id, ''))) < 8
     or length(btrim(coalesce(p_device_id, ''))) > 128
     or coalesce(p_token_hash, '') !~ '^[0-9a-f]{64}$' then
    return query select false, null::uuid;
    return;
  end if;

  update public.maidie_invite_codes
     set status = 'used', used_at = now()
   where lower(code) = lower(btrim(p_code))
     and status = 'unused'
  returning id into v_invite_id;

  if v_invite_id is null then
    return query select false, null::uuid;
    return;
  end if;

  insert into public.maidie_users(
    token,
    device_id,
    invite_code_id,
    status
  )
  values (
    p_token_hash,
    btrim(p_device_id),
    v_invite_id,
    'active'
  )
  returning id into v_user_id;

  return query select true, v_user_id;
exception
  when unique_violation then
    return query select false, null::uuid;
end;
$$;

revoke all on function public.redeem_maidie_invite(text, text, text)
  from public, anon, authenticated;
grant execute on function public.redeem_maidie_invite(text, text, text)
  to service_role;
