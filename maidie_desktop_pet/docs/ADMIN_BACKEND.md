# Maidie 生产授权后台

管理后台由两个独立部分组成：

- `admin_web/`：私有生产管理页，不持有数据库密钥。
- `supabase/functions/maidie-admin`：生产管理 API，负责密码验证、会话和数据库写入。

## 生产限制

管理 API 只有同时满足以下条件才会响应，否则返回 `404`：

```text
DENO_DEPLOYMENT_ID=<Supabase 托管环境自动提供>
maidie_admin_runtime.environment=production
maidie_admin_runtime.enabled=true
maidie_admin_runtime.proxy_secret_hash=<站点代理密钥的 SHA-256>
```

管理页的服务端代理必须设置：

```text
MAIDIE_ADMIN_API_URL=https://<project-ref>.supabase.co/functions/v1/maidie-admin
MAIDIE_ADMIN_PROXY_SECRET=<与 Supabase 相同的代理密钥>
```

代理密钥原文只存于私有站点的加密环境变量，数据库仅保存摘要。管理员会话密钥在首次设置密码时由服务端随机生成，并存于仅 `service_role` 可读的管理配置表。不要把这些值写进仓库或客户端配置。

## 首次使用

生产站点以仅所有者可见方式部署。首次打开时，页面会要求设置管理员密码：

- 至少 12 个字符，最多 128 个字符。
- 服务端使用 PBKDF2-SHA256、随机盐和 210,000 次迭代保存摘要。
- 密码原文不会写入数据库、日志或浏览器存储。
- 登录成功后签发 8 小时 `HttpOnly + Secure + SameSite=Strict` 会话 Cookie。
- 同一来源连续失败 5 次后暂停登录 15 分钟。

## 可用功能

- 批量生成 1–50 个随机邀请码。
- 查看未使用、已使用和已禁用的邀请码。
- 禁用尚未使用的邀请码。
- 查看邀请码对应的用户授权。
- 立即吊销或恢复用户 token。
- 查看最近的后台操作审计记录。

吊销用户后，`_shared/maidie_auth.ts` 会拒绝该 token 对 AI、Tavily 和千问视觉的全部调用。

## 安全边界

- 管理站点应保持仅所有者可见。
- 浏览器只调用同源站点代理，不会获得 Supabase service-role/secret key。
- Supabase 管理 API 还会校验独立代理密钥，直接请求函数 URL 不会得到后台数据。
- 后台表全部启用 RLS，并撤销 `anon` 与 `authenticated` 的表权限。
- 管理员密码不能用于恢复；若确实遗忘，应由项目所有者通过受控数据库迁移重置配置，不提供公开“忘记密码”入口。
