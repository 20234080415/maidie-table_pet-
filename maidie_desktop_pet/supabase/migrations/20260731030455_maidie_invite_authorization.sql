create table public.maidie_invite_codes (
  id bigint generated always as identity primary key,
  code text not null,
  status text not null default 'unused'
    check (status in ('unused', 'used', 'disabled')),
  created_at timestamptz not null default now(),
  used_at timestamptz
);

create unique index maidie_invite_codes_code_unique
  on public.maidie_invite_codes (lower(code));

create table public.maidie_users (
  id uuid primary key default gen_random_uuid(),
  token text not null unique,
  device_id text not null unique,
  created_at timestamptz not null default now()
);

comment on column public.maidie_users.token is
  'SHA-256 hash of the opaque token returned once to the Maidie client.';

alter table public.maidie_invite_codes enable row level security;
alter table public.maidie_users enable row level security;

revoke all on table public.maidie_invite_codes from anon, authenticated;
revoke all on table public.maidie_users from anon, authenticated;
grant select, insert, update on table public.maidie_invite_codes to service_role;
grant select, insert, update on table public.maidie_users to service_role;
grant usage, select on sequence public.maidie_invite_codes_id_seq to service_role;

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

  insert into public.maidie_users(token, device_id)
  values (p_token_hash, btrim(p_device_id))
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
