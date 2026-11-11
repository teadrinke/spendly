# Spec: Login and Logout

## Overview
Turn the existing static login page into a working sign-in flow and replace the `/logout` stub. `POST /login` verifies the submitted email and password against the `users` table, stores the user's id in the Flask session, and redirects to the profile page. `GET /logout` clears the session and returns the user to the landing page. This is Step 3 of the roadmap: registration (Step 2) created real users, and every logged-in page (profile, expenses) needs a session to know who is signed in. The navbar also becomes session-aware.

## Depends on
- Step 1 — Database setup (`users` table, `get_db()`)
- Step 2 — Registration (`get_user_by_email()`, users with hashed passwords, `/login?registered=1` redirect)

## Routes
- `GET /login` — render the sign-in form (already exists); if already logged in, redirect to `/profile` — public
- `POST /login` — validate credentials, set session, redirect to `/profile` on success; re-render form with an error and status 400 on failure — public
- `GET /logout` — clear the session, redirect to `/` — logged-in (harmless if already logged out)

`/login` keeps the same route function and URL; change the decorator to `methods=["GET", "POST"]`. `/logout` replaces its stub string return. `/profile` stays a stub and is not implemented in this step; the redirect target only needs the URL to exist.

## Database changes
No database changes. `get_user_by_email()` from Step 2 is sufficient for lookup; password verification uses `check_password_hash` on the returned row's `password_hash`.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html` — re-populate the `email` input from the submitted value on error (never the password); keep the existing `{% if error %}` block and `url_for('login')` form action
  - `templates/base.html` — navbar shows "Sign in" / "Get started" when logged out, and "Sign out" (link to `url_for('logout')`) when `session.user_id` is set

## Files to change
- `app.py` — import `session`, `check_password_hash`; set `app.secret_key`; accept POST on `/login`; implement `/logout`
- `templates/login.html` — see above
- `templates/base.html` — session-aware navbar
- `CLAUDE.md` — mark `GET/POST /login` and `GET /logout` as implemented in the routes table

## Files to create
- `tests/test_login_logout.py` — pytest tests for login and logout (use a temporary DB, not the real `expense_tracker.db`)

## New dependencies
No new dependencies. Uses Flask's built-in `session` and `werkzeug.security.check_password_hash` (werkzeug is already in `requirements.txt`).

## Validation rules
- `email`: trimmed and lower-cased before lookup
- `password`: taken as-is (not trimmed)
- Unknown email or wrong password → the same generic error "Invalid email or password." (never reveal which one was wrong); HTTP status 400; no session is set
- Empty email or password → same generic error
- Successful login stores only `user_id` in the session (no password hash, no email)

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug — verify with `check_password_hash`, never compare plaintext
- Use CSS variables — never hardcode hex values (reuse existing `.auth-error` styles; any new navbar style goes in `static/css/style.css` using variables, no inline `<style>`)
- All templates extend `base.html`
- DB logic lives in `database/db.py` only; the route reads the form, calls helpers, and renders or redirects
- Use `url_for()` for every link and redirect — no hardcoded URLs
- `app.secret_key` is read from an environment variable (e.g. `SECRET_KEY`) with a development fallback; never commit a real secret
- Call `session.clear()` on logout (and before setting the user id on login, to avoid session fixation)
- Do not implement other stub routes (`/profile`, `/expenses/*`)
- Keep the app on port 5001

## Definition of done
- [ ] `GET /login` renders the form with status 200 when logged out
- [ ] Logging in as `demo@spendly.com` / `demo123` redirects (302) to `/profile`
- [ ] Email matching is case-insensitive and ignores surrounding whitespace
- [ ] A wrong password shows "Invalid email or password." with status 400 and sets no session
- [ ] An unregistered email shows the same error message as a wrong password
- [ ] On error, the email field keeps the entered value and the password field is empty
- [ ] After a successful login, the navbar shows "Sign out" instead of "Sign in" / "Get started"
- [ ] `GET /login` while logged in redirects to `/profile`
- [ ] `GET /logout` clears the session and redirects (302) to `/`; the navbar then shows "Sign in" again
- [ ] A user registered via `/register` can immediately sign in with the same credentials
- [ ] No raw SQL string formatting appears in `app.py` or `database/db.py`
- [ ] `pytest tests/test_login_logout.py` passes
- [ ] The app starts on port 5001 without errors
