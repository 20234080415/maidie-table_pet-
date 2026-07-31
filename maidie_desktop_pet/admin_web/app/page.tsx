"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Invite = {
  id: number;
  code: string;
  status: "unused" | "used" | "disabled";
  note: string;
  created_at: string;
  used_at: string | null;
};

type MaidieUser = {
  id: string;
  device_id: string;
  invite_code_id: number | null;
  status: "active" | "revoked";
  created_at: string;
  revoked_at: string | null;
};

type AuditEntry = {
  id: number;
  action: string;
  target_type: string;
  target_id: string;
  created_at: string;
};

type Overview = {
  invites: Invite[];
  users: MaidieUser[];
  audit: AuditEntry[];
  stats: {
    invite_total: number;
    invite_unused: number;
    invite_used: number;
    invite_disabled: number;
    user_active: number;
    user_revoked: number;
  };
};

type Phase = "loading" | "setup" | "login" | "dashboard" | "unavailable";

const actionNames: Record<string, string> = {
  admin_configured: "管理员密码已设置",
  login_succeeded: "管理员登录",
  login_failed: "密码验证失败",
  invites_created: "生成邀请码",
  invite_disabled: "禁用邀请码",
  user_revoked: "吊销用户授权",
  user_restored: "恢复用户授权",
};

async function adminRequest(path: string, init?: RequestInit) {
  const response = await fetch(`/api/admin/${path}`, {
    ...init,
    cache: "no-store",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  let payload: Record<string, unknown> = {};
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }
  return { response, payload };
}

function formatTime(value: string | null): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function Home() {
  const [phase, setPhase] = useState<Phase>("loading");
  const [overview, setOverview] = useState<Overview | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [count, setCount] = useState(5);
  const [prefix, setPrefix] = useState("MAIDIE");
  const [note, setNote] = useState("");

  const loadOverview = useCallback(async () => {
    const { response, payload } = await adminRequest("overview");
    if (response.status === 401) {
      setPhase("login");
      setOverview(null);
      return;
    }
    if (!response.ok) {
      setMessage("后台数据暂时无法读取，请稍后重试。");
      return;
    }
    setOverview(payload as unknown as Overview);
    setPhase("dashboard");
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      const { response, payload } = await adminRequest("bootstrap");
      if (!active) return;
      if (!response.ok) {
        setPhase("unavailable");
        return;
      }
      if (payload.configured !== true) {
        setPhase("setup");
        return;
      }
      if (payload.authenticated === true) {
        await loadOverview();
      } else {
        setPhase("login");
      }
    })();
    return () => {
      active = false;
    };
  }, [loadOverview]);

  const inviteCodeById = useMemo(
    () => new Map((overview?.invites ?? []).map((item) => [item.id, item.code])),
    [overview],
  );

  async function submitPassword(event: FormEvent, setup: boolean) {
    event.preventDefault();
    setMessage("");
    if (password.length < 12) {
      setMessage("管理员密码至少需要 12 个字符。");
      return;
    }
    if (setup && password !== confirmPassword) {
      setMessage("两次输入的密码不一致。");
      return;
    }
    setBusy(true);
    const { response, payload } = await adminRequest(setup ? "setup" : "login", {
      method: "POST",
      body: JSON.stringify({ password }),
    });
    setBusy(false);
    if (!response.ok) {
      const error = String(payload.error ?? "");
      setMessage(
        error === "too_many_attempts"
          ? "错误次数过多，请 15 分钟后再试。"
          : setup
            ? "管理员密码设置失败，请确认当前站点是生产私有站点。"
            : "密码不正确，请重试。",
      );
      return;
    }
    setPassword("");
    setConfirmPassword("");
    await loadOverview();
  }

  async function createInvites(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    const { response } = await adminRequest("invites", {
      method: "POST",
      body: JSON.stringify({ count, prefix, note }),
    });
    setBusy(false);
    if (!response.ok) {
      setMessage("邀请码生成失败，请稍后重试。");
      return;
    }
    setNote("");
    setMessage(`已生成 ${count} 个邀请码。`);
    await loadOverview();
  }

  async function mutate(path: string, successMessage: string) {
    setBusy(true);
    setMessage("");
    const { response } = await adminRequest(path, {
      method: "POST",
      body: "{}",
    });
    setBusy(false);
    if (!response.ok) {
      setMessage("操作未完成，数据可能已经发生变化。");
      return;
    }
    setMessage(successMessage);
    await loadOverview();
  }

  async function logout() {
    await adminRequest("logout", { method: "POST", body: "{}" });
    setOverview(null);
    setPhase("login");
    setMessage("");
  }

  if (phase === "loading") {
    return (
      <main className="center-shell">
        <section className="auth-card">
          <span className="eyebrow">Maidie Control</span>
          <h1>正在连接生产后台</h1>
          <div className="loading-bar" aria-label="加载中" />
        </section>
      </main>
    );
  }

  if (phase === "unavailable") {
    return (
      <main className="center-shell">
        <section className="auth-card">
          <span className="eyebrow">Production only</span>
          <h1>后台未在此环境开放</h1>
          <p>该管理页只连接 Maidie 的生产环境。请从已发布的私有站点访问。</p>
        </section>
      </main>
    );
  }

  if (phase === "setup" || phase === "login") {
    const setup = phase === "setup";
    return (
      <main className="center-shell">
        <section className="auth-card">
          <div className="brand-mark" aria-hidden="true">M</div>
          <span className="eyebrow">Maidie Control</span>
          <h1>{setup ? "设置管理员密码" : "管理员登录"}</h1>
          <p>
            {setup
              ? "这是生产后台的首次启用。密码至少 12 位，设置后不会再显示原文。"
              : "输入管理员密码以管理邀请码和用户授权。"}
          </p>
          <form onSubmit={(event) => void submitPassword(event, setup)}>
            <label htmlFor="password">管理员密码</label>
            <input
              id="password"
              type="password"
              autoComplete={setup ? "new-password" : "current-password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={12}
              maxLength={128}
              required
              autoFocus
            />
            {setup && (
              <>
                <label htmlFor="confirm-password">再次输入</label>
                <input
                  id="confirm-password"
                  type="password"
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  minLength={12}
                  maxLength={128}
                  required
                />
              </>
            )}
            {message && <p className="form-message error">{message}</p>}
            <button className="primary-button" type="submit" disabled={busy}>
              {busy ? "请稍候…" : setup ? "启用生产后台" : "登录"}
            </button>
          </form>
          <p className="security-note">密码验证、会话和数据库操作均在服务端完成。</p>
        </section>
      </main>
    );
  }

  if (!overview) return null;

  return (
    <main className="dashboard-shell">
      <header className="topbar">
        <div>
          <span className="eyebrow">Maidie Control</span>
          <h1>生产授权后台</h1>
        </div>
        <div className="topbar-actions">
          <span className="production-badge">生产环境</span>
          <button className="text-button" type="button" onClick={() => void logout()}>
            退出
          </button>
        </div>
      </header>

      {message && <div className="notice" role="status">{message}</div>}

      <section className="stat-grid" aria-label="授权概览">
        <article className="stat-card accent">
          <span>可用邀请码</span>
          <strong>{overview.stats.invite_unused}</strong>
          <small>共 {overview.stats.invite_total} 个</small>
        </article>
        <article className="stat-card">
          <span>已使用</span>
          <strong>{overview.stats.invite_used}</strong>
          <small>{overview.stats.invite_disabled} 个已禁用</small>
        </article>
        <article className="stat-card">
          <span>活跃用户</span>
          <strong>{overview.stats.user_active}</strong>
          <small>{overview.stats.user_revoked} 个已吊销</small>
        </article>
      </section>

      <section className="panel create-panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Create</span>
            <h2>生成邀请码</h2>
          </div>
          <p>一次最多生成 50 个，随机码不会在客户端保存服务商密钥。</p>
        </div>
        <form className="create-form" onSubmit={(event) => void createInvites(event)}>
          <label>
            数量
            <input
              type="number"
              min={1}
              max={50}
              value={count}
              onChange={(event) => setCount(Number(event.target.value))}
            />
          </label>
          <label>
            前缀
            <input
              value={prefix}
              maxLength={12}
              onChange={(event) => setPrefix(event.target.value.toUpperCase())}
            />
          </label>
          <label className="note-field">
            备注
            <input
              value={note}
              maxLength={200}
              placeholder="例如：首批内测"
              onChange={(event) => setNote(event.target.value)}
            />
          </label>
          <button className="primary-button compact" type="submit" disabled={busy}>
            生成
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Invites</span>
            <h2>邀请码</h2>
          </div>
          <p>仅未使用的邀请码可以禁用。</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>邀请码</th>
                <th>状态</th>
                <th>备注</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {overview.invites.map((invite) => (
                <tr key={invite.id}>
                  <td>
                    <button
                      className="code-button"
                      type="button"
                      title="点击复制"
                      onClick={() => {
                        void navigator.clipboard.writeText(invite.code);
                        setMessage("邀请码已复制。");
                      }}
                    >
                      {invite.code}
                    </button>
                  </td>
                  <td>
                    <span className={`status ${invite.status}`}>
                      {invite.status === "unused"
                        ? "未使用"
                        : invite.status === "used"
                          ? "已使用"
                          : "已禁用"}
                    </span>
                  </td>
                  <td>{invite.note || "—"}</td>
                  <td>{formatTime(invite.created_at)}</td>
                  <td>
                    {invite.status === "unused" ? (
                      <button
                        className="danger-button"
                        type="button"
                        disabled={busy}
                        onClick={() =>
                          void mutate(`invites/${invite.id}/disable`, "邀请码已禁用。")
                        }
                      >
                        禁用
                      </button>
                    ) : "—"}
                  </td>
                </tr>
              ))}
              {overview.invites.length === 0 && (
                <tr><td colSpan={5} className="empty-cell">还没有邀请码</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Users</span>
            <h2>用户授权</h2>
          </div>
          <p>吊销后，客户端原 token 会立即失效。</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>用户</th>
                <th>来源邀请码</th>
                <th>状态</th>
                <th>激活时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {overview.users.map((user) => (
                <tr key={user.id}>
                  <td className="mono">{user.id.slice(0, 8)}…</td>
                  <td className="mono">
                    {user.invite_code_id
                      ? inviteCodeById.get(user.invite_code_id) ?? `#${user.invite_code_id}`
                      : "—"}
                  </td>
                  <td>
                    <span className={`status ${user.status}`}>
                      {user.status === "active" ? "可用" : "已吊销"}
                    </span>
                  </td>
                  <td>{formatTime(user.created_at)}</td>
                  <td>
                    <button
                      className={user.status === "active" ? "danger-button" : "restore-button"}
                      type="button"
                      disabled={busy}
                      onClick={() =>
                        void mutate(
                          `users/${user.id}/${user.status === "active" ? "revoke" : "restore"}`,
                          user.status === "active" ? "用户授权已吊销。" : "用户授权已恢复。",
                        )
                      }
                    >
                      {user.status === "active" ? "吊销" : "恢复"}
                    </button>
                  </td>
                </tr>
              ))}
              {overview.users.length === 0 && (
                <tr><td colSpan={5} className="empty-cell">还没有激活用户</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel audit-panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Audit</span>
            <h2>最近操作</h2>
          </div>
        </div>
        <ol className="audit-list">
          {overview.audit.map((entry) => (
            <li key={entry.id}>
              <span>{actionNames[entry.action] ?? entry.action}</span>
              <time>{formatTime(entry.created_at)}</time>
            </li>
          ))}
          {overview.audit.length === 0 && <li className="empty-audit">暂无记录</li>}
        </ol>
      </section>
    </main>
  );
}
