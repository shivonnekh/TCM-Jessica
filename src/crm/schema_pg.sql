-- TCM-Jessica CRM schema (PostgreSQL)
-- Mirrors schema.sql (SQLite) but uses PG-native types.

CREATE TABLE IF NOT EXISTS users (
    phone           TEXT PRIMARY KEY,
    name            TEXT,
    status          TEXT NOT NULL DEFAULT 'new',
    age             INTEGER,
    location        TEXT,
    district        TEXT,
    constitution    TEXT NOT NULL DEFAULT 'unknown',
    pain_points     TEXT NOT NULL DEFAULT '[]',
    products_pitched   TEXT NOT NULL DEFAULT '[]',
    products_purchased TEXT NOT NULL DEFAULT '[]',
    notes           TEXT NOT NULL DEFAULT '',
    tags            TEXT NOT NULL DEFAULT '[]',
    temp_state      TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_users_constitution ON users(constitution);
CREATE INDEX IF NOT EXISTS idx_users_updated_at ON users(updated_at);

CREATE TABLE IF NOT EXISTS messages (
    id              SERIAL PRIMARY KEY,
    phone           TEXT NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    media_urls      TEXT NOT NULL DEFAULT '[]',
    wa_message_id   TEXT,
    turn_id         TEXT,
    at              TEXT NOT NULL,
    FOREIGN KEY (phone) REFERENCES users(phone) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_phone_at ON messages(phone, at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_turn_id ON messages(turn_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_wa_id ON messages(wa_message_id)
    WHERE wa_message_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS appointments (
    id              SERIAL PRIMARY KEY,
    phone           TEXT NOT NULL,
    clinic_id       TEXT NOT NULL,
    date            TEXT NOT NULL,
    time            TEXT NOT NULL,
    mode            TEXT NOT NULL,
    status          TEXT NOT NULL,
    booked_at       TEXT NOT NULL,
    FOREIGN KEY (phone) REFERENCES users(phone) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_appointments_phone ON appointments(phone);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(date);

-- Proactive broadcast tracking — per-user weekly cap (max 2/week)
CREATE TABLE IF NOT EXISTS user_broadcasts (
    id              SERIAL PRIMARY KEY,
    phone           TEXT NOT NULL,
    sent_at         TEXT NOT NULL,
    condition_code  TEXT NOT NULL,
    iso_week        TEXT NOT NULL,
    FOREIGN KEY (phone) REFERENCES users(phone) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_broadcasts_phone_week
    ON user_broadcasts(phone, iso_week);
