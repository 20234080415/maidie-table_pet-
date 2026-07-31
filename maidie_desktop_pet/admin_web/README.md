# Maidie Production Admin

Maidie 邀请码和用户授权的私有生产管理页。

## 安全模型

- 站点以仅所有者可见方式部署。
- 浏览器只访问同源 `/api/admin/*` 代理。
- 代理使用生产环境变量调用 Supabase `maidie-admin`。
- 管理员密码仅发送到服务端，并以 PBKDF2 加盐摘要保存。
- 本地开发环境未配置生产变量时只显示“后台未开放”。

## 本地检查

```bash
npm ci
npm run build
npm test
```

生产环境变量见 `.env.example`。不要提交真实代理密钥。
