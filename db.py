# db.py - everything about the SQLite database lives here.
# SQLite = a whole database inside ONE file (cybernews.db). No server needed.

import os
import sqlite3

from flask import current_app, g
from werkzeug.security import generate_password_hash

from seed_data import SAMPLE_ARTICLES


def get_db():
    """Open one database connection per request and reuse it (stored in g)."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row          # lets me write row["title"]
        g.db.execute("PRAGMA foreign_keys = ON")  # makes ON DELETE CASCADE work
    return g.db


def close_db(error=None):
    """Close the connection at the end of every request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create the tables and fill them with sample data."""
    db = get_db()
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, encoding="utf-8") as f:
        db.executescript(f.read())

    # Demo admin account for LOCAL TESTING ONLY. Set ADMIN_PASSWORD to change it.
    admin_password = os.environ.get("ADMIN_PASSWORD", "ChangeMe-Admin123!")
    db.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        ("admin", generate_password_hash(admin_password), "admin"),
    )

    # Sample articles. The "?" placeholders keep data and SQL separate.
    for a in SAMPLE_ARTICLES:
        db.execute(
            """INSERT INTO articles
               (title, summary, content, source, source_url, category,
                published_date, is_featured, is_sample, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1)""",
            (a["title"], a["summary"], a["content"], a["source"], a["source_url"],
             a["category"], a["published_date"], a["is_featured"]),
        )
    db.commit()


def init_app(app):
    """Connect the database helpers to the Flask app."""
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command():
        """flask --app web_app init-db  ->  wipe and recreate the database."""
        init_db()
        print("Database created with sample data.")

    # First run: if the .db file does not exist yet, create it automatically.
    if not os.path.exists(app.config["DATABASE"]):
        with app.app_context():
            init_db()
