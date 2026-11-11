import pytest
from werkzeug.security import check_password_hash

from database import db

VALID = {"name": "Jane Doe", "email": "jane@example.com", "password": "secret123"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    db.seed_db()

    import app as app_module

    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def count_users():
    conn = db.get_db()
    try:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        conn.close()


def post(client, **overrides):
    return client.post("/register", data={**VALID, **overrides})


def test_get_register_renders_form(client):
    resp = client.get("/register")
    assert resp.status_code == 200
    assert b'action="/register"' in resp.data


def test_valid_post_redirects_to_login_with_banner(client):
    resp = post(client)
    assert resp.status_code == 302
    assert resp.headers["Location"].startswith("/login")
    assert "Set-Cookie" not in resp.headers

    followed = client.get(resp.headers["Location"])
    assert b"Account created successfully" in followed.data


@pytest.mark.parametrize("query", ["", "?registered=0", "?registered=abc"])
def test_login_without_flag_has_no_banner(client, query):
    assert b"Account created" not in client.get("/login" + query).data


def test_user_stored_hashed_and_normalised(client):
    before = count_users()
    post(client, name="  Jane Doe  ", email="  Jane@Example.COM ")
    assert count_users() == before + 1
    user = db.get_user_by_email("jane@example.com")
    assert user["email"] == "jane@example.com"
    assert user["name"] == "Jane Doe"
    assert user["password_hash"] != VALID["password"]
    assert check_password_hash(user["password_hash"], VALID["password"])
    assert user["created_at"]


@pytest.mark.parametrize("email", ["demo@spendly.com", "Demo@Spendly.com"])
def test_duplicate_email_rejected(client, email):
    before = count_users()
    resp = post(client, email=email)
    assert resp.status_code == 400
    assert b"already exists" in resp.data
    assert count_users() == before


def test_password_length_boundary(client):
    before = count_users()
    resp = post(client, password="1234567")
    assert resp.status_code == 400
    assert count_users() == before
    assert post(client, password="12345678").status_code == 302


@pytest.mark.parametrize("name", ["", "   "])
def test_blank_name_rejected(client, name):
    before = count_users()
    assert post(client, name=name).status_code == 400
    assert count_users() == before


@pytest.mark.parametrize("email", ["", "foo", "@x.com", "foo@", "a@b@c"])
def test_invalid_email_rejected(client, email):
    before = count_users()
    assert post(client, email=email).status_code == 400
    assert count_users() == before


def test_empty_post_is_400_not_500(client):
    assert client.post("/register", data={}).status_code == 400


def test_error_repopulates_fields_but_not_password(client):
    resp = post(client, password="short")
    assert b'value="Jane Doe"' in resp.data
    assert b'value="jane@example.com"' in resp.data
    assert b"short" not in resp.data.replace(b"Min. 8 characters", b"")


def test_name_is_escaped(client):
    resp = post(client, name='"><script>x</script>', password="short")
    assert b"<script>x</script>" not in resp.data


def test_integrity_error_race_is_handled(client, monkeypatch):
    import app as app_module

    monkeypatch.setattr(app_module, "get_user_by_email", lambda email: None)
    before = count_users()
    resp = post(client, email="demo@spendly.com")
    assert resp.status_code == 400
    assert b"already exists" in resp.data
    assert count_users() == before
