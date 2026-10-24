# tests/test_app.py - automatic tests. Run with:  python -m pytest -v
# Each test gets a fresh temporary database, so tests never touch cybernews.db.

import os
import re
import sys
import tempfile

import pytest

TMP_DB = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE"] = TMP_DB
os.environ["ADMIN_PASSWORD"] = "ChangeMe-Admin123!"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db  # noqa: E402
from web_app import app  # noqa: E402

ADMIN_PW = "ChangeMe-Admin123!"


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.app_context():
        db.init_db()
    with app.test_client() as c:
        yield c


def token(client, url):
    """Open a page and pull the hidden csrf_token out of the HTML."""
    page = client.get(url).get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)


def login(client, username, password):
    return client.post("/login", data={"username": username, "password": password,
                                       "csrf_token": token(client, "/login")})


def register(client, username, password):
    return client.post("/register", data={"username": username, "password": password, "confirm": password,
                                          "csrf_token": token(client, "/register")})


def test_public_pages_load(client):
    for url in ["/", "/news", "/article/1", "/login", "/register", "/contact"]:
        assert client.get(url).status_code == 200, url


def test_home_has_featured_and_cards(client):
    html = client.get("/").get_data(as_text=True)
    assert "Featured stories" in html and 'class="card feature"' in html
    assert "<header>" in html and "<nav>" in html and "<footer>" in html


def test_unknown_article_is_404(client):
    assert client.get("/article/9999").status_code == 404


def test_api_search_and_filters(client):
    all_rows = client.get("/api/articles").get_json()
    assert len(all_rows) == 12
    assert all(r["category"] == "Phishing" for r in client.get("/api/articles?category=Phishing").get_json())
    assert all(r["source"] == "CISA" for r in client.get("/api/articles?source=CISA").get_json())
    assert all(r["published_date"] >= "2026-10-18" for r in client.get("/api/articles?date_from=2026-10-18").get_json())
    assert len(client.get("/api/articles?q=ransomware").get_json()) >= 1


def test_sql_injection_in_search_is_harmless(client):
    r = client.get("/api/articles", query_string={"q": "' OR 1=1 --"})
    assert r.status_code == 200 and r.get_json() == []      # treated as plain text
    client.get("/api/articles", query_string={"q": "'; DROP TABLE articles; --"})
    assert len(client.get("/api/articles").get_json()) == 12  # table still there


def test_register_login_logout_and_audit(client):
    assert register(client, "alice", "alicepass123").status_code == 302
    r = login(client, "alice", "alicepass123")
    assert r.status_code == 302
    assert "alice" in client.get("/").get_data(as_text=True)
    client.post("/logout", data={"csrf_token": token(client, "/")})
    assert "Log in" in client.get("/").get_data(as_text=True)


def test_password_is_hashed(client):
    register(client, "bob", "bobpass1234")
    with app.app_context():
        row = db.get_db().execute("SELECT password_hash FROM users WHERE username='bob'").fetchone()
    assert "bobpass1234" not in row["password_hash"] and row["password_hash"].startswith(("scrypt:", "pbkdf2:"))


def test_wrong_password_rejected_and_logged(client):
    r = login(client, "admin", "wrong-password")
    assert r.status_code == 401 and "Wrong username or password" in r.get_data(as_text=True)
    with app.app_context():
        n = db.get_db().execute("SELECT COUNT(*) FROM login_audit WHERE event='login_failed'").fetchone()[0]
    assert n == 1


def test_duplicate_username_and_short_password(client):
    assert register(client, "admin", "whatever123").status_code == 400
    assert register(client, "carol", "short").status_code == 400


def test_normal_user_gets_403_on_admin_pages(client):
    register(client, "dave", "davepass123")
    login(client, "dave", "davepass123")
    for url in ["/admin", "/admin/articles/new", "/admin/articles/1/edit", "/admin/audit-log"]:
        assert client.get(url).status_code == 403, url
    t = token(client, "/")
    assert client.post("/admin/articles/1/delete", data={"csrf_token": t}).status_code == 403


def test_logged_out_visitor_is_sent_to_login(client):
    r = client.get("/admin")
    assert r.status_code == 302 and "/login" in r.headers["Location"]
    assert client.get("/bookmarks").status_code == 302


def test_admin_crud(client):
    login(client, "admin", ADMIN_PW)
    assert client.get("/admin").status_code == 200
    t = token(client, "/admin/articles/new")
    data = {"title": "Test article from pytest", "summary": "A summary that is long enough.",
            "content": "Body", "source": "SecurityWeek", "source_url": "https://www.securityweek.com/",
            "category": "Research", "published_date": "2026-10-23", "csrf_token": t}
    r = client.post("/admin/articles/new", data=data)
    assert r.status_code == 302
    new_id = int(r.headers["Location"].rstrip("/").split("/")[-1])
    data["title"] = "Edited title"
    data["csrf_token"] = token(client, f"/admin/articles/{new_id}/edit")
    assert client.post(f"/admin/articles/{new_id}/edit", data=data).status_code == 302
    assert "Edited title" in client.get(f"/article/{new_id}").get_data(as_text=True)
    assert client.post(f"/admin/articles/{new_id}/delete", data={"csrf_token": token(client, "/admin")}).status_code == 302
    assert client.get(f"/article/{new_id}").status_code == 404


def test_javascript_url_rejected(client):
    login(client, "admin", ADMIN_PW)
    data = {"title": "Bad link", "summary": "A summary that is long enough.", "source": "Evil",
            "source_url": "javascript:alert(1)", "category": "Research", "published_date": "2026-10-23",
            "csrf_token": token(client, "/admin/articles/new")}
    r = client.post("/admin/articles/new", data=data)
    assert r.status_code == 400 and "must start with http" in r.get_data(as_text=True)


def test_xss_title_is_escaped(client):
    login(client, "admin", ADMIN_PW)
    data = {"title": "<script>alert('xss')</script>", "summary": "Testing escaping safely.",
            "source": "Test", "source_url": "https://example.com/", "category": "Research",
            "published_date": "2026-10-23", "csrf_token": token(client, "/admin/articles/new")}
    r = client.post("/admin/articles/new", data=data)
    page = client.get(r.headers["Location"]).get_data(as_text=True)
    assert "<script>alert('xss')</script>" not in page
    assert "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;" in page


def test_bookmarks(client):
    register(client, "erin", "erinpass123")
    login(client, "erin", "erinpass123")
    client.post("/bookmark/2", data={"csrf_token": token(client, "/article/2")})
    page = client.get("/bookmarks").get_data(as_text=True)
    assert "Northwind Clinics" in page
    client.post("/bookmark/2", data={"csrf_token": token(client, "/article/2")})  # toggle off
    assert "Northwind Clinics" not in client.get("/bookmarks").get_data(as_text=True)


def test_csrf_missing_token_rejected(client):
    r = client.post("/login", data={"username": "admin", "password": ADMIN_PW})
    assert r.status_code == 400 and "CSRF" in r.get_data(as_text=True)
    r = client.post("/submit-message", data={"name": "x", "email": "x@example.com", "message": "hi"})
    assert r.status_code == 400


def test_open_redirect_blocked(client):
    r = client.post("/login?next=https://evil.example/", data={
        "username": "admin", "password": ADMIN_PW, "csrf_token": token(client, "/login")})
    assert r.headers["Location"] == "/"


def test_contact_form_saved(client):
    r = client.post("/submit-message", data={"name": "Alice", "email": "alice@example.com",
                                             "message": "Suggest a source", "csrf_token": token(client, "/contact")})
    assert "Thanks for reaching out, Alice!" in r.get_data(as_text=True)


def test_filter_bar_lists_categories_and_sources(client):
    html = client.get("/").get_data(as_text=True)
    assert '<option value="Phishing"' in html and '<option value="CISA"' in html
