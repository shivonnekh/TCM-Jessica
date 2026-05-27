-- TCM-Jessica CRM schema (SQLite)
-- Migrations are forward-only; never DROP in production.

CREATE TABLE IF NOT EXISTS users (
    phone           TEXT PRIMARY KEY,
    name            TEXT,
    status          TEXT NOT NULL DEFAULT 'new',
    age             INTEGER,
    location        TEXT,
    district        TEXT,
    constitution    TEXT NOT NULL DEFAULT 'unknown',
    pain_points     TEXT NOT NULL DEFAULT '[]',  -- JSON array
    products_pitched   TEXT NOT NULL DEFAULT '[]',
    products_purchased TEXT NOT NULL DEFAULT '[]',
    notes           TEXT NOT NULL DEFAULT '',
    tags            TEXT NOT NULL DEFAULT '[]',
    temp_state      TEXT NOT NULL DEFAULT '{}',  -- JSON object for cross-turn flow state
    -- Menstrual cycle tracking (optional — female users only)
    last_period_start  TEXT,                      -- ISO date YYYY-MM-DD, nullable
    cycle_length_days  INTEGER NOT NULL DEFAULT 28,
    -- 辨證 layer — JSON array of ObservedPattern entries, append-only
    observed_patterns  TEXT NOT NULL DEFAULT '[]',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_users_constitution ON users(constitution);
CREATE INDEX IF NOT EXISTS idx_users_updated_at ON users(updated_at);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    phone           TEXT NOT NULL,
    role            TEXT NOT NULL,         -- 'user' | 'jessica'
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
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    phone           TEXT NOT NULL,
    clinic_id       TEXT NOT NULL,
    date            TEXT NOT NULL,
    time            TEXT NOT NULL,
    mode            TEXT NOT NULL,       -- 'in_person' | 'online_video'
    status          TEXT NOT NULL,       -- 'proposed' | 'confirmed' | ...
    booked_at       TEXT NOT NULL,
    FOREIGN KEY (phone) REFERENCES users(phone) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_appointments_phone ON appointments(phone);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(date);

-- Tongue diagnosis history — for progress tracking (舌診進度追蹤)
CREATE TABLE IF NOT EXISTS tongue_photos (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    phone                TEXT NOT NULL,
    photo_url            TEXT NOT NULL,
    captured_at          TEXT NOT NULL,
    tongue_colour        TEXT NOT NULL DEFAULT '',
    coating_colour       TEXT NOT NULL DEFAULT '',
    coating_thickness    TEXT NOT NULL DEFAULT '',
    coating_moisture     TEXT NOT NULL DEFAULT '',
    body_shape           TEXT NOT NULL DEFAULT '',
    teeth_marks          INTEGER NOT NULL DEFAULT 0,
    cracks               INTEGER NOT NULL DEFAULT 0,
    raw_analysis         TEXT NOT NULL DEFAULT '',
    constitution_at_time TEXT NOT NULL DEFAULT 'unknown',
    FOREIGN KEY (phone) REFERENCES users(phone) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tongue_photos_phone_captured
    ON tongue_photos(phone, captured_at DESC);

-- Proactive broadcast tracking — per-user weekly cap (max 2/week)
CREATE TABLE IF NOT EXISTS user_broadcasts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    phone           TEXT NOT NULL,
    sent_at         TEXT NOT NULL,          -- ISO-8601 with tz
    condition_code  TEXT NOT NULL,          -- e.g. 'heatwave', 'cold_front'
    iso_week        TEXT NOT NULL,          -- e.g. '2026-W21'
    FOREIGN KEY (phone) REFERENCES users(phone) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_broadcasts_phone_week
    ON user_broadcasts(phone, iso_week);
