-- schema.sql - the tables (like sheets in a spreadsheet) for CyberNews
-- Running this file again starts with a clean, empty database.

DROP TABLE IF EXISTS bookmarks;
DROP TABLE IF EXISTS login_audit;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS articles;
DROP TABLE IF EXISTS users;

-- People who can log in. We NEVER store the real password, only a hash of it.
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- The news articles shown on the site.
CREATE TABLE articles (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    title          TEXT    NOT NULL,
    summary        TEXT    NOT NULL,
    content        TEXT    NOT NULL DEFAULT '',
    source         TEXT    NOT NULL,
    source_url     TEXT    NOT NULL,
    category       TEXT    NOT NULL,
    published_date TEXT    NOT NULL,              -- YYYY-MM-DD
    is_featured    INTEGER NOT NULL DEFAULT 0,    -- 1 = show in "Featured stories"
    is_sample      INTEGER NOT NULL DEFAULT 0,    -- 1 = placeholder text I wrote, not real news
    created_by     INTEGER REFERENCES users(id),
    created_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Which user saved which article (one row per bookmark).
CREATE TABLE bookmarks (
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, article_id)
);

-- Every login attempt (good or bad) and every logout. Only admins can read it.
CREATE TABLE login_audit (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT    NOT NULL,
    event      TEXT    NOT NULL,   -- login_success, login_failed, logout, register
    ip_address TEXT,
    user_agent TEXT,
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Messages sent with the Contact form (from Ex 4 POSTman).
CREATE TABLE messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL,
    message    TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
