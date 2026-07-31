from __future__ import annotations

import json
import logging
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Iterator
from uuid import uuid4


logger = logging.getLogger(__name__)


class ConversationMemory:
    """SQLite-backed recent chat and long-term user memory store."""

    DEFAULT_CHAT_LIMIT = 100
    MAX_CHAT_LIMIT = 500
    SENSITIVE_PATTERN = re.compile(
        r"api[_ -]?key|password|passwd|密码|口令|secret|token|bearer\s+|"
        r"sk-[a-z0-9_-]+|身份证|银行卡|信用卡|cvv|私钥|private key|"
        r"手机号|电话号码|邮箱|住址|家庭地址|病历|诊断|健康隐私|"
        r"[\w.+-]+@[\w.-]+\.[a-z]{2,}|\b1[3-9]\d{9}\b",
        re.IGNORECASE,
    )
    CHAT_SENSITIVE_VALUE_PATTERN = re.compile(
        r"(?:api[_ -]?key|password|passwd|密码|口令|secret|token)"
        r"\s*(?:是|为|[:=])\s*[^\s,，。;；]{4,}|"
        r"bearer\s+[a-z0-9._~+/=-]{8,}|"
        r"sk-[a-z0-9_-]{8,}|"
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----|"
        r"[\w.+-]+@[\w.-]+\.[a-z]{2,}|"
        r"(?<!\d)1[3-9]\d{9}(?!\d)|"
        r"(?<!\d)\d{17}[\dXx](?!\d)|"
        r"(?<!\d)\d{16,19}(?!\d)",
        re.IGNORECASE,
    )

    def __init__(self, path: Path, limit: int = DEFAULT_CHAT_LIMIT):
        self.path = path
        self.limit = min(self.MAX_CHAT_LIMIT, max(1, int(limit)))
        self._lock = RLock()
        self._generation = 0
        self._last_search_query = ""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def set_last_search_query(self, query: str) -> None:
        """Keep retry context in memory only; it is not persisted as chat."""
        self._last_search_query = str(query).strip()

    def get_last_search_query(self) -> str:
        return self._last_search_query

    def generation_token(self) -> int:
        with self._lock:
            return self._generation

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL CHECK(type IN ('chat', 'fact', 'preference')),
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    importance REAL NOT NULL DEFAULT 0.5,
                    created_at DATETIME NOT NULL,
                    UNIQUE(type, key)
                )
            """)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_priority "
                "ON memories(importance DESC, created_at DESC)"
            )

    def get_recent(self) -> list[dict[str, str]]:
        try:
            with self._lock, self._connect() as connection:
                rows = connection.execute(
                    "SELECT value, created_at FROM memories WHERE type='chat' "
                    "ORDER BY id DESC LIMIT ?", (self.limit,)
                ).fetchall()
            result = []
            for row in reversed(rows):
                try:
                    payload = json.loads(row["value"])
                except (json.JSONDecodeError, TypeError):
                    logger.warning(
                        "Skipping malformed recent-chat row created at %s",
                        row["created_at"],
                    )
                    continue
                result.append({
                    "message": str(payload.get("message", "")),
                    "response": str(payload.get("response", "")),
                    "time": str(row["created_at"]),
                })
            return result
        except (sqlite3.Error, OSError, TypeError):
            logger.warning("Unable to read recent chats from %s", self.path, exc_info=True)
            return []

    def save(self, message: str, response: str) -> bool:
        safe_message = self._redact_chat_text(message)
        safe_response = self._redact_chat_text(response)
        payload = json.dumps(
            {"message": safe_message, "response": safe_response}, ensure_ascii=False
        )
        now = datetime.now().isoformat(timespec="seconds")
        try:
            with self._lock, self._connect() as connection:
                connection.execute(
                    "INSERT INTO memories(type, key, value, importance, created_at) "
                    "VALUES('chat', ?, ?, ?, ?)",
                    (uuid4().hex, payload, 0.1, now),
                )
                connection.execute("""
                    DELETE FROM memories WHERE type='chat' AND id NOT IN (
                        SELECT id FROM memories WHERE type='chat'
                        ORDER BY id DESC LIMIT ?
                    )
                """, (self.limit,))
            return True
        except (sqlite3.Error, OSError):
            logger.warning("Unable to save recent chat to %s", self.path, exc_info=True)
            return False

    def save_memory(
        self, memory_type: str, key: str, value: str, importance: float = 0.7
    ) -> bool:
        memory_type = str(memory_type).strip().lower()
        key, value = str(key).strip(), str(value).strip()
        if memory_type not in ("fact", "preference") or not key or not value:
            return False
        if self._is_sensitive(f"{key} {value}"):
            return False
        importance = max(0.0, min(1.0, float(importance)))
        try:
            with self._lock, self._connect() as connection:
                connection.execute("""
                    INSERT INTO memories(type, key, value, importance, created_at)
                    VALUES(?, ?, ?, ?, ?)
                    ON CONFLICT(type, key) DO UPDATE SET
                        value=excluded.value,
                        importance=MAX(memories.importance, excluded.importance),
                        created_at=excluded.created_at
                """, (
                    memory_type, key[:200], value[:2000], importance,
                    datetime.now().isoformat(timespec="seconds"),
                ))
            return True
        except (sqlite3.Error, OSError, TypeError, ValueError):
            return False

    def save_extracted(
        self,
        extracted: dict[str, Any],
        *,
        generation: int | None = None,
        source_message: str = "",
    ) -> bool:
        if not isinstance(extracted, dict):
            return False
        with self._lock:
            if generation is not None and generation != self._generation:
                return False
            for plural, memory_type, default_importance in (
                ("facts", "fact", 0.7),
                ("preferences", "preference", 0.9),
            ):
                items = extracted.get(plural, [])
                if not isinstance(items, list):
                    continue
                for item in items[:20]:
                    if isinstance(item, dict):
                        key = str(item.get("key", ""))
                        value = str(item.get("value", ""))
                        if not self._is_supported_extracted_memory(
                            key, value, source_message
                        ):
                            continue
                        self.save_memory(
                            memory_type,
                            key,
                            value,
                            float(item.get("importance", default_importance)),
                        )
            return True

    @staticmethod
    def _is_supported_extracted_memory(
        key: str, value: str, source_message: str
    ) -> bool:
        """Reject identity/roleplay memories inferred from the assistant's own reply."""
        source = str(source_message or "").strip()
        if not source:
            return True
        normalized_key = str(key).strip().lower()
        normalized_value = str(value).strip().lower()
        identity_tokens = (
            "name", "nickname", "form_of_address", "姓名", "名字", "昵称", "称呼", "叫法",
        )
        if any(token in normalized_key for token in identity_tokens):
            explicit_name = re.search(
                r"(?:叫我|称呼我|喊我|我叫|我的(?:名字|昵称)(?:是|叫))",
                source,
                re.IGNORECASE,
            )
            return bool(
                explicit_name
                and normalized_value
                and normalized_value in source.lower()
            )
        role_tokens = (
            "roleplay", "role_play", "persona", "角色扮演", "人格", "人设", "角色风格",
        )
        if any(token in normalized_key for token in role_tokens):
            return bool(
                re.search(r"(?:我喜欢|我偏好|我希望|我想要|请用|改成|设为)", source)
                and re.search(r"(?:人格|人设|角色|扮演|语气|风格|爱豆|女仆|傲娇)", source)
            )
        return True

    def load_memories(self, limit: int = 20) -> list[dict[str, Any]]:
        try:
            with self._lock, self._connect() as connection:
                rows = connection.execute(
                    "SELECT type, key, value, importance, created_at FROM memories "
                    "WHERE type IN ('fact', 'preference') "
                    "ORDER BY importance DESC, created_at DESC LIMIT ?",
                    (min(20, max(1, int(limit))),),
                ).fetchall()
            return [dict(row) for row in rows]
        except (sqlite3.Error, OSError, TypeError, ValueError):
            return []

    def prompt_context(self) -> str:
        memories = self.load_memories(20)
        if not memories:
            return ""
        lines = ["用户背景信息（仅用于更贴心地回答，不要声称掌握未提供的信息）："]
        for item in memories:
            label = "偏好" if item["type"] == "preference" else "事实"
            lines.append(f"- [{label}] {item['key']}：{item['value']}")
        return "\n".join(lines)

    def delete_conversation_history(self) -> bool:
        return self._delete("type='chat'", reset_conversation_state=True)

    def delete_long_term_memory(self) -> bool:
        return self._delete("type IN ('fact', 'preference')")

    def delete_all_memory(self) -> bool:
        return self._delete(reset_conversation_state=True)

    def clear(self) -> bool:
        """Compatibility alias for callers that expect the old full reset."""
        return self.delete_all_memory()

    def _delete(self, where: str = "", *, reset_conversation_state: bool = False) -> bool:
        with self._lock:
            self._generation += 1
            if reset_conversation_state:
                self._last_search_query = ""
            statement = "DELETE FROM memories"
            if where:
                statement += f" WHERE {where}"
            try:
                with self._connect() as connection:
                    connection.execute(statement)
                return True
            except (sqlite3.Error, OSError):
                return False

    def clear_search_context(self) -> None:
        with self._lock:
            self._last_search_query = ""

    @classmethod
    def _is_sensitive(cls, text: str) -> bool:
        return bool(cls.SENSITIVE_PATTERN.search(text))

    @classmethod
    def _redact_chat_text(cls, text: str) -> str:
        return cls.CHAT_SENSITIVE_VALUE_PATTERN.sub("[已隐藏敏感信息]", str(text))

    def can_extract(self, message: str, response: str) -> bool:
        return not self._is_sensitive(f"{message} {response}")
