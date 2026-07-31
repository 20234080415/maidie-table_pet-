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
  v_invite_status text;
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

  select id, status
    into v_invite_id, v_invite_status
    from public.maidie_invite_codes
   where lower(code) = lower(btrim(p_code))
   for update;

  if v_invite_id is null or v_invite_status = 'disabled' then
    return query select false, null::uuid;
    return;
  end if;

  if v_invite_status = 'used' then
    update public.maidie_users
       set token = p_token_hash
     where invite_code_id = v_invite_id
       and device_id = btrim(p_device_id)
       and status = 'active'
    returning id into v_user_id;

    return query
      select v_user_id is not null, v_user_id;
    return;
  end if;

  update public.maidie_invite_codes
     set status = 'used', used_at = now()
   where id = v_invite_id
     and status = 'unused';

  if not found then
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

comment on function public.redeem_maidie_invite(text, text, text) is
  'Redeems an unused invite, or rotates the token when the same active device retries the same invite.';

revoke all on function public.redeem_maidie_invite(text, text, text)
  from public, anon, authenticated;
grant execute on function public.redeem_maidie_invite(text, text, text)
  to service_role;
