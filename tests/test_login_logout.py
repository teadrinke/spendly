import pytest

from database import db

DEMO = {"email": "demo@spendly.com", "password": "demo123"}
GENERIC_ERROR = b"Invalid email or password."


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    db.seed_db()

    import app as app_module

    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


def login(client, **overrides):
    return client.post("/login", data={**DEMO, **overrides})


def test_get_login_renders_form(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b'action="/login"' in resp.data


def test_valid_login_redirects_to_profile(client):
    resp = login(client)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")
    with client.session_transaction() as sess:
        assert set(sess.keys()) == {"user_id"}
        assert sess["user_id"] == db.get_user_by_email(DEMO["email"])["id"]


def test_email_is_case_insensitive_and_trimmed(client):
    resp = login(client, email="  DEMO@Spendly.com ")
    assert resp.status_code == 302


def test_wrong_password_rejected(client):
    resp = login(client, password="wrong-password")
    assert resp.status_code == 400
    assert GENERIC_ERROR in resp.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_unknown_email_same_error(client):
    resp = login(client, email="nobody@example.com")
    assert resp.status_code == 400
    assert GENERIC_ERROR in resp.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


@pytest.mark.parametrize(
    "overrides",
    [{"email": ""}, {"password": ""}, {"email": "", "password": ""}],
)
def test_empty_fields_rejected(client, overrides):
    resp = login(client, **overrides)
    assert resp.status_code == 400
    assert GENERIC_ERROR in resp.data


def test_error_keeps_email_not_password(client):
    resp = login(client, email="Demo@Spendly.com", password="badpass999")
    assert b'value="demo@spendly.com"' in resp.data
    assert b"badpass999" not in resp.data


def test_error_email_is_escaped(client):
    resp = login(client, email='"><script>alert(1)</script>', password="x")
    assert b"<script>alert(1)</script>" not in resp.data


def test_navbar_logged_out(client):
    body = client.get("/").data
    assert b"Sign in" in body
    assert b"Get started" in body
    assert b"Sign out" not in body


def test_navbar_logged_in(client):
    login(client)
    body = client.get("/").data
    assert b"Sign out" in body
    assert b"Get started" not in body


def test_get_login_while_logged_in_redirects(client):
    login(client)
    resp = client.get("/login")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")


def test_logout_clears_session(client):
    login(client)
    resp = client.get("/logout")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")
    with client.session_transaction() as sess:
        assert "user_id" not in sess
    assert b"Sign in" in client.get("/").data


def test_logout_when_logged_out_is_harmless(client):
    resp = client.get("/logout")
    assert resp.status_code == 302


def test_registered_user_can_login(client):
    client.post(
        "/register",
        data={"name": "Jane", "email": "jane@example.com", "password": "secret123"},
    )
    resp = login(client, email="jane@example.com", password="secret123")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")


def test_login_clears_stale_session_data(client):
    with client.session_transaction() as sess:
        sess["junk"] = 1
    login(client)
    with client.session_transaction() as sess:
        assert "junk" not in sess
        assert "user_id" in sess


def test_next_param_ignored(client):
    resp = client.post("/login?next=//evil.com", data=DEMO)
    assert resp.headers["Location"].endswith("/profile")
    assert "evil.com" not in resp.headers["Location"]
