import aiosqlite
from app.config import DB_PATH

INIT_SQL = """
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK(type IN ('bot', 'user')),
    name TEXT NOT NULL,
    token_or_session TEXT,
    phone TEXT,
    api_id INTEGER,
    api_hash TEXT,
    status TEXT DEFAULT 'disconnected',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS forward_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    source_account_id INTEGER NOT NULL,
    source_chat_id TEXT NOT NULL,
    source_chat_title TEXT,
    dest_account_id INTEGER,
    dest_chat_id TEXT,
    dest_chat_title TEXT,
    delivery_agent TEXT DEFAULT 'account',
    forward_method TEXT DEFAULT 'copy',
    webhook_mode TEXT DEFAULT 'off',
    webhook_url TEXT,
    keyword_allow TEXT DEFAULT '',
    keyword_block TEXT DEFAULT '',
    media_types TEXT DEFAULT 'all',
    user_whitelist TEXT DEFAULT '',
    user_blacklist TEXT DEFAULT '',
    prefix_text TEXT DEFAULT '',
    cooldown_seconds INTEGER DEFAULT 0,
    schedule_from TEXT DEFAULT '',
    schedule_to TEXT DEFAULT '',
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (source_account_id) REFERENCES accounts(id) ON DELETE CASCADE,
    FOREIGN KEY (dest_account_id) REFERENCES accounts(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS forward_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id INTEGER NOT NULL,
    source_msg_id INTEGER,
    source_chat_title TEXT,
    message_text TEXT,
    message_media_type TEXT,
    dest_info TEXT,
    status TEXT NOT NULL,
    error TEXT,
    latency_ms INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (rule_id) REFERENCES forward_rules(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS webhook_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    secret TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS telegram_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


async def get_db():
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    return db


MIGRATIONS = [
    "ALTER TABLE forward_rules ADD COLUMN delivery_agent TEXT DEFAULT 'account'",
    "ALTER TABLE forward_rules ADD COLUMN forward_method TEXT DEFAULT 'copy'",
    "ALTER TABLE forward_rules ADD COLUMN keyword_allow TEXT DEFAULT ''",
    "ALTER TABLE forward_rules ADD COLUMN keyword_block TEXT DEFAULT ''",
    "ALTER TABLE forward_rules ADD COLUMN media_types TEXT DEFAULT 'all'",
    "ALTER TABLE forward_rules ADD COLUMN user_whitelist TEXT DEFAULT ''",
    "ALTER TABLE forward_rules ADD COLUMN user_blacklist TEXT DEFAULT ''",
    "ALTER TABLE forward_rules ADD COLUMN prefix_text TEXT DEFAULT ''",
    "ALTER TABLE forward_rules ADD COLUMN cooldown_seconds INTEGER DEFAULT 0",
    "ALTER TABLE forward_rules ADD COLUMN schedule_from TEXT DEFAULT ''",
    "ALTER TABLE forward_rules ADD COLUMN schedule_to TEXT DEFAULT ''",
    "ALTER TABLE forward_logs ADD COLUMN source_chat_title TEXT",
    "ALTER TABLE forward_logs ADD COLUMN message_text TEXT",
    "ALTER TABLE forward_logs ADD COLUMN message_media_type TEXT",
]


async def init_db():
    db = await get_db()
    for statement in INIT_SQL.split(";"):
        stmt = statement.strip()
        if stmt:
            await db.execute(stmt)
    await db.commit()

    for migration in MIGRATIONS:
        try:
            await db.execute(migration)
            await db.commit()
        except Exception:
            pass

    # migrate old delivery_mode → delivery_agent + forward_method
    try:
        cursor = await db.execute("SELECT id, forward_mode, delivery_mode FROM forward_rules WHERE delivery_agent = 'account' AND forward_method = 'copy' AND delivery_mode IS NOT NULL AND delivery_mode != 'account'")
        rows = await cursor.fetchall()
        for row in rows:
            dm = row["delivery_mode"]
            fm = row["forward_mode"]
            agent = "account"
            method = fm
            if dm == "bot":
                agent = "bot"
            elif dm == "account_fallback_bot":
                agent = "account_fallback_bot"
            if fm == "forward_copy":
                method = "forward_fallback_copy"
            await db.execute(
                "UPDATE forward_rules SET delivery_agent = ?, forward_method = ?, forward_mode = NULL, delivery_mode = NULL WHERE id = ?",
                (agent, method, row["id"]),
            )
        await db.commit()
    except Exception:
        pass

    await db.close()


async def get_config(key: str) -> str | None:
    db = await get_db()
    cursor = await db.execute("SELECT value FROM telegram_config WHERE key = ?", (key,))
    row = await cursor.fetchone()
    await db.close()
    return row["value"] if row else None


async def set_config(key: str, value: str):
    db = await get_db()
    await db.execute(
        "INSERT OR REPLACE INTO telegram_config (key, value) VALUES (?, ?)",
        (key, value),
    )
    await db.commit()
    await db.close()
