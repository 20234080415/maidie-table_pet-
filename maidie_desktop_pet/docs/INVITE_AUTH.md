# Maidie 邀请码授权

邀请码授权是自定义 API 之外的第二种 AI 服务方式，不替换设置页、模型选择或原有 Agent 调用链。

## 运行结构

```text
Maidie AIClient
├─ custom   -> 用户自己的 OpenAI-compatible API
├─ invite   -> Supabase maidie-chat   -> 服务端 DeepSeek
└─ disabled -> 未配置提示 / 本地确定性工具

NetworkPlugin
├─ custom   -> 用户自己的 Tavily Key
└─ invite   -> Supabase maidie-search -> 服务端 Tavily

VisionService
├─ custom   -> 用户自己的千问 Key + Workspace
└─ invite   -> Supabase maidie-vision -> 服务端千问视觉
```

客户端激活时调用 `verify-invite`，提交 `invite_code` 和随机安装标识 `device_id`。成功后只保存返回的原始 `user_token`。数据库 `maidie_users.token` 保存的是 SHA-256 哈希，因此数据库读取权限泄露时也不会直接得到可用 token。

## Supabase 资源

- `maidie_invite_codes`：邀请码、状态、创建时间、使用时间。
- `maidie_users`：token 哈希、设备标识、创建时间。
- `redeem_maidie_invite`：仅授予 `service_role` 的原子兑换函数，避免同一邀请码并发重复使用。
- `verify-invite`：无 Supabase Auth JWT；函数内部校验输入并通过服务端密钥兑换邀请码。
- `maidie-chat`：无 Supabase Auth JWT；函数内部验证 Maidie Bearer token，限制消息数量和长度，再调用默认模型。
- `maidie-search`：验证同一个 Bearer token 后调用服务端 Tavily，并返回原有 `NetworkResult` 结构。
- `maidie-vision`：验证同一个 Bearer token 后调用服务端千问视觉；截图仍由客户端隐私开关和明确意图控制。

两个表均启用 RLS，`anon` 和 `authenticated` 没有表权限。Supabase Secret Key / legacy service-role key 只在 Edge Function 内使用，不进入客户端。

## 云端 Secrets

生产聊天前必须在 Supabase Edge Function Secrets 中设置：

```text
DEEPSEEK_API_KEY=<服务端默认模型 Key>
TAVILY_API_KEY=<服务端默认搜索 Key>
DASHSCOPE_API_KEY=<服务端千问视觉 Key>
DASHSCOPE_WORKSPACE_ID=<服务端千问 Workspace ID>
```

可选覆盖：

```text
MAIDIE_AI_BASE_URL=https://api.deepseek.com
MAIDIE_AI_CHAT_MODEL=deepseek-v4-flash
MAIDIE_AI_TECHNICAL_MODEL=deepseek-v4-pro
QWEN_VL_REGION=cn-beijing
QWEN_VL_MODEL=qwen3-vl-flash
```

不要把上述值写进仓库或 `packaging/config.json`。修改 Secrets 后无需重新打包客户端。

## 生成邀请码

邀请码由运营人员在 Supabase 后台写入，例如：

```sql
insert into public.maidie_invite_codes(code) values ('MAIDIE-EXAMPLE-001');
```

邀请码默认状态为 `unused`，成功兑换后原子更新为 `used` 并写入 `used_at`。

## 扩展新服务

客户端的 `core/cloud.py` 是统一服务注册表。新增例如语音服务时：

1. 在 `cloud` 配置中增加 `voice_path`。
2. 新增一个实现现有语音接口的 invite adapter，并用 `cloud_endpoint(cloud, "voice")` 取地址。
3. 新增独立 Edge Function；用 `_shared/maidie_auth.ts` 验证同一个 Bearer token。
4. 将供应商密钥放进 Edge Function Secrets。

未知服务会自动按 `<service>_path` 解析，因此不需要修改邀请码表、token 保存逻辑或 Agent 主流程。独立函数也便于分别限流、计费和替换供应商。

## 生产管理后台

邀请码生成、禁用、用户 token 吊销和审计记录由独立的生产后台管理。后台不会进入 Maidie 客户端安装包，也不会暴露服务商密钥。部署和首次设置管理员密码的说明见 [`ADMIN_BACKEND.md`](ADMIN_BACKEND.md)。
