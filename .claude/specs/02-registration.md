# Spec: Registration

## Overview
Turn the existing static registration page into a working sign-up flow. `GET /register` already renders `register.html`; this step adds the `POST /register` handler that validates the submitted form, hashes the password, inserts a new row into `users`, on success the user is shown a success message and then redirects to the login page. It sits at Step 2 of the roadmap because login, logout and every logged-in page (profile, expenses) need real users in the database first. Registration does not log the user in — sessions belong to Step 3.

## Depends on
- Step 1 — Database setup (`users` table, `get_db()`, `init_db()`)

## Routes
- `GET /register` — render the registration form (already exists; accepts POST after this step) — public
- `POST /register` — validate form, create user, redirect to `/login` on success, re-render form with an error on failure — public

Same route function and URL; change the decorator to `methods=["GET", "POST"]`. No other new routes.

## Database changes
No schema changes. The existing `users` table (`id`, `name`, `email UNIQUE NOT NULL`, `password_hash`, `created_at`) is sufficient.

Two new helper functions in `database/db.py` (no inline SQL in routes):
- `get_user_by_email(email)` — returns the matching `sqlite3.Row` or `None`
- `create_user(name, email, password)` — hashes the password with `generate_password_hash`, inserts the row with a parameterised query, returns the new user id; raises `sqlite3.IntegrityError` if the email already exists (UNIQUE constraint is the final guard against races)

## Templates
- **Create:** none
- **Modify:** `templates/register.html`
  - Form `action` uses `url_for('register')` instead of the hardcoded `/register`
  - Re-populate `name` and `email` inputs from submitted values on error (never re-populate the password)
  - Keep the existing `{% if error %}` block for error messages

## Files to change
- `app.py` — accept POST on `/register`, validation, call db helpers, redirect
- `database/db.py` — add `get_user_by_email()` and `create_user()`
- `templates/register.html` — see above
- `CLAUDE.md` — update the note that says `db.py` provides only `get_db()`, `init_db()`, `seed_db()` so it lists the new helpers

## Files to create
- `tests/test_registration.py` — pytest tests for the registration flow (use a temporary DB, not the real `expense_tracker.db`)

## New dependencies
No new dependencies. Uses `werkzeug.security` (already in `requirements.txt`) and Flask's `request`, `redirect`, `url_for`.

## Validation rules
- `name`: required, trimmed, not empty
- `email`: required, trimmed, lower-cased before storing and lookup, must contain `@` with text on both sides (basic check; the browser's `type="email"` is not trusted)
- `password`: required, minimum 8 characters (matches the form placeholder)
- Email already registered → error "An account with this email already exists"
- Any validation failure → re-render `register.html` with `error` set and HTTP status 200 (or 400); never a raw string return and nothing is inserted

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — no f-strings in SQL
- Passwords hashed with werkzeug (`generate_password_hash`); never store or log plaintext
- Use CSS variables — never hardcode hex values (reuse the existing `.auth-error` styles; add no inline `<style>`)
- All templates extend `base.html`
- DB logic lives in `database/db.py` only; the route just reads the form, calls helpers, and renders or redirects
- Use `url_for()` for every link and redirect — no hardcoded URLs
- Catch `sqlite3.IntegrityError` from `create_user()` as the duplicate-email fallback
- Do not implement stub routes (`/logout`, `/profile`, `/expenses/*`) and do not add sessions, `secret_key`, or auto-login — those are Step 3
- Keep the app on port 5001

## Definition of done
- [ ] `GET /register` still renders the form with status 200
- [ ] Submitting valid name, email and an 8+ character password redirects (302) to `/login`
- [ ] The new user appears in `users` with a hashed `password_hash` (not the plaintext) and a `created_at` value
- [ ] Submitting an email that is already registered (including `demo@spendly.com` and different letter case) shows an error and creates no second row
- [ ] Submitting a password shorter than 8 characters shows an error and creates no row
- [ ] Submitting an empty or whitespace-only name, or an invalid email, shows an error and creates no row
- [ ] On any error, the name and email fields keep the entered values and the password field is empty
- [ ] The form action in `register.html` is generated with `url_for()`
- [ ] No raw SQL string formatting appears in `app.py` or `database/db.py`
- [ ] `pytest tests/test_registration.py` passes
- [ ] The app starts on port 5001 without errors
