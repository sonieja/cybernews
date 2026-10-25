# CyberNews 🛡️

My individual student project: a website that collects cybersecurity news in one place.
It is built with **Flask** (Python), **SQLite** (database), **Jinja2** templates, plain **CSS** and a little **JavaScript**.

It grew step by step out of the CyberNews Tracker exercises (Ex 3 Newsman: `/news` page with templates,
Ex 4 POSTman: contact form) and now has a database, accounts, an admin area and security features.

> ⚠️ **Sample data:** the articles that come with the project are placeholder stories I wrote for practice
> (with made-up companies like Contoso and Northwind). They are marked with a yellow **Sample** badge.
> The source names are real news sites, but the links only go to their **home pages**.
> The admin can import real headlines from The Hacker News RSS feed.

> 🤖 **AI prototype:** before building this, I generated a prototype with Lovable ("CyberNews Pulse").
> Screenshots are in [`ai_prototype/`](ai_prototype/), and the comparison is in [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md).

## Features

- Header, navigation, main content and footer on every page (one shared `base.html` layout)
- Home dashboard with **featured stories**, article cards and a category list
- **Live search and filters** (category, source, date) – JavaScript `fetch()` calls a Flask JSON API (`/api/articles`)
- Individual article pages (`/article/<id>`)
- SQLite database: articles, users, bookmarks, login audit log, contact messages
- Register, log in, log out (sessions), **hashed passwords**
- **Roles**: `user` (read + bookmark) and `admin` (add / edit / delete articles, audit log, RSS import)
- **Bookmarks** for logged-in users
- **Login audit log** for admins (successful logins, failed logins, logouts, registrations)
- Contact form (from Ex 4) saved to the database and shown to admins
- Phone-friendly layout

## Security measures

| Risk | What I did |
|---|---|
| Stolen passwords | Passwords stored only as hashes (`werkzeug.security.generate_password_hash`) |
| SQL injection | Every query uses `?` placeholders, never string gluing |
| XSS | Jinja2 autoescaping, JavaScript uses `textContent`, links must start with `http(s)://` |
| CSRF | `Flask-WTF CSRFProtect` – every POST form has a hidden `csrf_token` |
| Normal user doing admin things | `@admin_required` decorator returns **403 Forbidden** |
| Secret key in code | `SECRET_KEY` comes from an environment variable |
| Session cookie theft | Cookie is `HttpOnly` and `SameSite=Lax`; session is cleared on login |
| Guessing usernames | Same "Wrong username or password" message for both cases |
| Open redirect | `?next=` only allows paths on this site |
| Debugger on a server | Debug mode is **off** unless you set `FLASK_DEBUG=1` |

## Setup and run (Linux / macOS)

```bash
cd cybernews_project
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export ADMIN_PASSWORD="choose-your-own-strong-password"   # optional, see below

python web_app.py
```

Open <http://127.0.0.1:5000> in the browser.

The database file `cybernews.db` is created automatically on the first run, with sample articles.
To wipe it and start again:

```bash
flask --app web_app init-db
```

## Demo admin account (LOCAL TESTING ONLY)

| Username | Password |
|---|---|
| `admin` | `ChangeMe-Admin123!` |

> 🔴 This default password is **only for testing on your own computer**. It is used when
> `ADMIN_PASSWORD` is not set at the moment the database is created. Set `ADMIN_PASSWORD`
> (then run `flask --app web_app init-db`) before showing the site to anyone else, and never deploy with it.

New accounts made on the Register page are always normal users.

## Run the automatic tests

```bash
python -m pytest -v
```

18 tests check pages, login, wrong passwords, 403 for normal users, admin add/edit/delete,
bookmarks, CSRF, XSS escaping and SQL injection in the search.

## Project structure

```
cybernews_project/
├── web_app.py          # Flask app: routes, login, roles, admin, API
├── db.py               # SQLite connection + create tables + sample data
├── schema.sql          # the database tables
├── seed_data.py        # sample (placeholder) articles
├── requirements.txt
├── static/
│   ├── style.css       # dark "terminal" look + phone layout
│   └── app.js          # live search/filter with fetch()
├── templates/          # Jinja2 HTML templates (base.html is the shared layout)
├── tests/test_app.py   # pytest tests
└── screenshots/        # pictures of the working site
```

## Known limitations

- No rate limiting yet, so someone could try many passwords (they would show up in the audit log).
- Runs on Flask's development server; a real deployment needs HTTPS and a server like gunicorn.
- No password reset or email verification.
