# web_app.py - CyberNews: my cybersecurity news website (individual project)
#
# It grew out of the CyberNews Tracker exercises (Ex 3 Newsman, Ex 4 POSTman).
# Big parts:
#   - Flask routes that show pages (HTML) and one JSON API for JavaScript
#   - SQLite database (db.py) for articles, users, bookmarks, audit log, messages
#   - Login with sessions, hashed passwords, and roles (user / admin)
#   - Security: CSRF tokens, ? placeholders in SQL, Jinja autoescaping

import os
import re
import html
import secrets
import urllib.request
from datetime import date
from functools import wraps

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config.update(
    # The secret key signs the session cookie. It comes from an environment
    # variable so it is never written in the code. If it is missing, we make a
    # random one (fine for practice, but everyone gets logged out on restart).
    SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
    DATABASE=os.environ.get("DATABASE", os.path.join(BASE_DIR, "cybernews.db")),
    SESSION_COOKIE_HTTPONLY=True,    # JavaScript cannot read the session cookie
    SESSION_COOKIE_SAMESITE="Lax",   # cookie is not sent on most cross-site requests
)

csrf = CSRFProtect()  # every POST form must include a secret csrf_token (switched on below)
db.init_app(app)

CATEGORIES = ["Vulnerabilities", "Ransomware", "Phishing", "Malware", "Data Breach",
              "Cloud Security", "Research", "Advice", "News (RSS)"]
HACKER_NEWS_RSS = "https://feeds.feedburner.com/TheHackersNews"


# ---------------------------------------------------------------------------
# Login helpers
# ---------------------------------------------------------------------------

@app.before_request
def load_logged_in_user():
    """Before every request: look up who is logged in (or None)."""
    user_id = session.get("user_id")
    g.user = None
    if user_id is not None:
        g.user = db.get_db().execute(
            "SELECT id, username, role FROM users WHERE id = ?", (user_id,)
        ).fetchone()


# Switch on CSRF protection AFTER load_logged_in_user, so even the
# "security check failed" page still knows who is logged in.
csrf.init_app(app)


def login_required(view):
    """Decorator: only logged-in users may open this page."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in first.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    """Decorator: only admins. Logged-in normal users get 403 Forbidden."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("login", next=request.path))
        if g.user["role"] != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def audit(username, event):
    """Write one line to the login audit log."""
    database = db.get_db()
    database.execute(
        "INSERT INTO login_audit (username, event, ip_address, user_agent) VALUES (?, ?, ?, ?)",
        (username[:50], event, request.remote_addr, (request.user_agent.string or "")[:200]),
    )
    database.commit()


def is_safe_next(target):
    """Only allow redirects to pages on MY site (stops 'open redirect' tricks)."""
    return bool(target) and target.startswith("/") and not target.startswith("//")


# ---------------------------------------------------------------------------
# Article helpers
# ---------------------------------------------------------------------------

def search_articles(q="", category="", source="", date_from=""):
    """Find articles. User text only goes in as ? parameters, never glued into SQL."""
    sql = "SELECT * FROM articles WHERE 1=1"
    params = []
    if q:
        sql += " AND (title LIKE ? OR summary LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    if category:
        sql += " AND category = ?"
        params.append(category)
    if source:
        sql += " AND source = ?"
        params.append(source)
    if date_from:
        sql += " AND published_date >= ?"
        params.append(date_from)
    sql += " ORDER BY published_date DESC, id DESC"
    return db.get_db().execute(sql, params).fetchall()


def all_sources():
    rows = db.get_db().execute("SELECT DISTINCT source FROM articles ORDER BY source").fetchall()
    return [r["source"] for r in rows]


def get_article_or_404(article_id):
    article = db.get_db().execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
    if article is None:
        abort(404)
    return article


def validate_article_form(form):
    """Check the add/edit form on the SERVER. Returns (data, list_of_errors)."""
    data = {
        "title": form.get("title", "").strip(),
        "summary": form.get("summary", "").strip(),
        "content": form.get("content", "").strip(),
        "source": form.get("source", "").strip(),
        "source_url": form.get("source_url", "").strip(),
        "category": form.get("category", "").strip(),
        "published_date": form.get("published_date", "").strip(),
        "is_featured": 1 if form.get("is_featured") else 0,
    }
    errors = []
    if not (3 <= len(data["title"]) <= 200):
        errors.append("Title must be 3-200 characters.")
    if not (10 <= len(data["summary"]) <= 500):
        errors.append("Summary must be 10-500 characters.")
    if len(data["content"]) > 10000:
        errors.append("Content is too long (max 10,000 characters).")
    if not (2 <= len(data["source"]) <= 100):
        errors.append("Source name must be 2-100 characters.")
    # Only http:// or https:// links. This blocks "javascript:..." links (a kind of XSS).
    if not re.match(r"^https?://[^\s<>\"']+$", data["source_url"]):
        errors.append("Source link must start with http:// or https://")
    if data["category"] not in CATEGORIES:
        errors.append("Please pick a category from the list.")
    try:
        date.fromisoformat(data["published_date"])
    except ValueError:
        errors.append("Date must look like YYYY-MM-DD.")
    return data, errors


@app.context_processor
def inject_globals():
    """Variables every template can use."""
    return {"categories": CATEGORIES, "current_year": date.today().year}


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    database = db.get_db()
    featured = database.execute(
        "SELECT * FROM articles WHERE is_featured = 1 ORDER BY published_date DESC LIMIT 3"
    ).fetchall()
    latest = search_articles()
    counts = database.execute(
        "SELECT category, COUNT(*) AS n FROM articles GROUP BY category ORDER BY n DESC"
    ).fetchall()
    return render_template("index.html", featured=featured, articles=latest,
                           counts=counts, sources=all_sources())


@app.route("/news")
def news():
    """Works WITHOUT JavaScript too: the filter form just reloads this page."""
    q = request.args.get("q", "").strip()[:100]
    category = request.args.get("category", "")
    source = request.args.get("source", "")
    date_from = request.args.get("date_from", "")
    articles = search_articles(q, category, source, date_from)
    return render_template("news.html", articles=articles, sources=all_sources(),
                           q=q, category=category, source=source, date_from=date_from)


@app.route("/article/<int:article_id>")
def article_detail(article_id):
    article = get_article_or_404(article_id)
    bookmarked = False
    if g.user:
        bookmarked = db.get_db().execute(
            "SELECT 1 FROM bookmarks WHERE user_id = ? AND article_id = ?",
            (g.user["id"], article_id)).fetchone() is not None
    return render_template("article.html", article=article, bookmarked=bookmarked)


@app.route("/api/articles")
def api_articles():
    """JSON for JavaScript (static/app.js). Same search, but data instead of HTML."""
    rows = search_articles(
        request.args.get("q", "").strip()[:100],
        request.args.get("category", ""),
        request.args.get("source", ""),
        request.args.get("date_from", ""),
    )
    return jsonify([
        {"id": r["id"], "title": r["title"], "summary": r["summary"], "source": r["source"],
         "category": r["category"], "published_date": r["published_date"],
         "is_sample": bool(r["is_sample"]), "url": url_for("article_detail", article_id=r["id"])}
        for r in rows
    ])


# Contact form (from Ex 4 POSTman), now saved in the database
@app.route("/contact")
def contact():
    return render_template("contact_form.html")


@app.route("/submit-message", methods=["POST"])
def submit_message():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()
    if not name or not email or not message or len(message) > 2000:
        return render_template("contact_form.html", error="Please fill in all fields (max 2000 characters)."), 400
    database = db.get_db()
    database.execute("INSERT INTO messages (name, email, message) VALUES (?, ?, ?)",
                     (name[:100], email[:200], message))
    database.commit()
    return render_template("confirmation.html", name=name)


# ---------------------------------------------------------------------------
# Accounts: register, login, logout
# ---------------------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        error = None
        if not re.match(r"^[A-Za-z0-9_.-]{3,30}$", username):
            error = "Username: 3-30 letters, numbers, dots, dashes or underscores."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif password != confirm:
            error = "The two passwords do not match."
        if error is None:
            database = db.get_db()
            try:
                # New accounts are ALWAYS normal users. Nobody can sign up as admin.
                database.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'user')",
                    (username, generate_password_hash(password)),
                )
                database.commit()
            except database.IntegrityError:  # UNIQUE username already taken
                error = "That username is already taken."
            else:
                audit(username, "register")
                flash("Account created. You can log in now.", "success")
                return redirect(url_for("login"))
        flash(error, "error")
        return render_template("register.html", username=username), 400
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = db.get_db().execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            audit(username or "(empty)", "login_failed")
            # Same message for "no such user" and "wrong password", so an
            # attacker cannot find out which usernames exist.
            flash("Wrong username or password.", "error")
            return render_template("login.html", username=username), 401
        session.clear()               # throw away any old session first
        session["user_id"] = user["id"]
        audit(username, "login_success")
        flash(f"Welcome back, {user['username']}!", "success")
        next_page = request.args.get("next", "")
        return redirect(next_page if is_safe_next(next_page) else url_for("home"))
    return render_template("login.html")


@app.route("/logout", methods=["POST"])  # POST + CSRF token, so a link on another site can't log you out
def logout():
    if g.user:
        audit(g.user["username"], "logout")
    session.clear()
    flash("You are logged out.", "success")
    return redirect(url_for("home"))


# ---------------------------------------------------------------------------
# Bookmarks (any logged-in user)
# ---------------------------------------------------------------------------

@app.route("/bookmarks")
@login_required
def bookmarks():
    rows = db.get_db().execute(
        """SELECT a.* FROM articles a
           JOIN bookmarks b ON b.article_id = a.id
           WHERE b.user_id = ? ORDER BY b.created_at DESC""",
        (g.user["id"],)).fetchall()
    return render_template("bookmarks.html", articles=rows)


@app.route("/bookmark/<int:article_id>", methods=["POST"])
@login_required
def toggle_bookmark(article_id):
    get_article_or_404(article_id)
    database = db.get_db()
    exists = database.execute("SELECT 1 FROM bookmarks WHERE user_id = ? AND article_id = ?",
                              (g.user["id"], article_id)).fetchone()
    if exists:
        database.execute("DELETE FROM bookmarks WHERE user_id = ? AND article_id = ?",
                         (g.user["id"], article_id))
        flash("Bookmark removed.", "success")
    else:
        database.execute("INSERT INTO bookmarks (user_id, article_id) VALUES (?, ?)",
                         (g.user["id"], article_id))
        flash("Saved to your bookmarks.", "success")
    database.commit()
    return redirect(url_for("article_detail", article_id=article_id))


# ---------------------------------------------------------------------------
# Admin area (role = admin only)
# ---------------------------------------------------------------------------

@app.route("/admin")
@admin_required
def admin_dashboard():
    database = db.get_db()
    stats = {
        "articles": database.execute("SELECT COUNT(*) FROM articles").fetchone()[0],
        "users": database.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "bookmarks": database.execute("SELECT COUNT(*) FROM bookmarks").fetchone()[0],
        "failed_logins": database.execute(
            "SELECT COUNT(*) FROM login_audit WHERE event = 'login_failed'").fetchone()[0],
    }
    articles = database.execute(
        "SELECT id, title, source, category, published_date, is_featured FROM articles "
        "ORDER BY published_date DESC, id DESC").fetchall()
    messages = database.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 5").fetchall()
    return render_template("admin_dashboard.html", stats=stats, articles=articles, messages=messages)


@app.route("/admin/articles/new", methods=["GET", "POST"])
@admin_required
def add_article():
    if request.method == "POST":
        data, errors = validate_article_form(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("article_form.html", article=data, mode="add"), 400
        database = db.get_db()
        cur = database.execute(
            """INSERT INTO articles (title, summary, content, source, source_url, category,
                                     published_date, is_featured, created_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data["title"], data["summary"], data["content"], data["source"], data["source_url"],
             data["category"], data["published_date"], data["is_featured"], g.user["id"]))
        database.commit()
        flash("Article added.", "success")
        return redirect(url_for("article_detail", article_id=cur.lastrowid))
    empty = {"published_date": date.today().isoformat(), "source_url": "https://"}
    return render_template("article_form.html", article=empty, mode="add")


@app.route("/admin/articles/<int:article_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_article(article_id):
    article = get_article_or_404(article_id)
    if request.method == "POST":
        data, errors = validate_article_form(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            data["id"] = article_id
            return render_template("article_form.html", article=data, mode="edit"), 400
        database = db.get_db()
        database.execute(
            """UPDATE articles SET title = ?, summary = ?, content = ?, source = ?, source_url = ?,
                   category = ?, published_date = ?, is_featured = ?, is_sample = 0
               WHERE id = ?""",
            (data["title"], data["summary"], data["content"], data["source"], data["source_url"],
             data["category"], data["published_date"], data["is_featured"], article_id))
        database.commit()
        flash("Article updated.", "success")
        return redirect(url_for("article_detail", article_id=article_id))
    return render_template("article_form.html", article=article, mode="edit")


@app.route("/admin/articles/<int:article_id>/delete", methods=["POST"])
@admin_required
def delete_article(article_id):
    get_article_or_404(article_id)
    database = db.get_db()
    database.execute("DELETE FROM articles WHERE id = ?", (article_id,))
    database.commit()
    flash("Article deleted.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/audit-log")
@admin_required
def audit_log():
    rows = db.get_db().execute(
        "SELECT * FROM login_audit ORDER BY id DESC LIMIT 200").fetchall()
    return render_template("audit_log.html", rows=rows)


@app.route("/admin/import-rss", methods=["POST"])
@admin_required
def import_rss():
    """Optional extra: pull real headlines from The Hacker News RSS feed."""
    try:
        import feedparser
        # Download with a timeout so the site does not hang if I'm offline.
        req = urllib.request.Request(HACKER_NEWS_RSS, headers={"User-Agent": "CyberNews-student-project"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            feed = feedparser.parse(resp.read())
    except Exception as e:  # no internet, DNS error, timeout...
        flash(f"Could not reach the RSS feed ({type(e).__name__}). Are you offline? Nothing was changed.", "error")
        return redirect(url_for("admin_dashboard"))

    database = db.get_db()
    added = 0
    for entry in feed.entries[:10]:
        link = entry.get("link", "")
        title = entry.get("title", "").strip()
        if not title or not link.startswith("https://"):
            continue
        if database.execute("SELECT 1 FROM articles WHERE source_url = ?", (link,)).fetchone():
            continue  # already imported
        # The feed summary can contain HTML tags. Strip them; Jinja escapes the rest anyway.
        summary = html.unescape(re.sub(r"<[^>]+>", "", entry.get("summary", ""))).strip()[:400] or title
        published = entry.get("published_parsed")
        pub_date = date(*published[:3]).isoformat() if published else date.today().isoformat()
        database.execute(
            """INSERT INTO articles (title, summary, content, source, source_url, category,
                                     published_date, is_featured, is_sample, created_by)
               VALUES (?, ?, ?, 'The Hacker News', ?, 'News (RSS)', ?, 0, 0, ?)""",
            (title[:200], summary, "Imported from The Hacker News RSS feed. Read the full story at the source link.",
             link, pub_date, g.user["id"]))
        added += 1
    database.commit()
    flash(f"RSS import finished: {added} new article(s) from The Hacker News.", "success")
    return redirect(url_for("admin_dashboard"))


# ---------------------------------------------------------------------------
# Friendly error pages
# ---------------------------------------------------------------------------

@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", code=403, title="403 - Forbidden",
                           text="You are logged in, but your account is not allowed to open this page. Admins only."), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, title="404 - Not found",
                           text="This page or article does not exist."), 404


@app.errorhandler(CSRFError)
def csrf_error(e):
    return render_template("error.html", code=400, title="400 - Security check failed",
                           text="The form was missing its CSRF security token (or it expired). Go back, reload the page and try again."), 400


if __name__ == "__main__":
    # Debug mode stays OFF unless I turn it on myself with FLASK_DEBUG=1.
    # Never run debug mode on a server other people can reach.
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("FLASK_DEBUG") == "1")
