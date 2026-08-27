# StockFlow production deployment

## Architecture and secrets

Supabase is used **only as PostgreSQL hosting**. StockFlow retains its FastAPI-managed users,
password hashes, session hashes, roles, and HttpOnly cookie. The browser needs no Supabase anon
key, service-role key, or database password. Only the private FastAPI environment receives
`DATABASE_URL`; SQLAlchemy remains the database access layer.

Build and expose one service so `/` serves React, `/api/*` serves FastAPI, and `/health` and
`/ready` are probes. Leave `VITE_API_URL` unset for same-origin requests. Use an encrypted URI:

```text
APP_ENV=production
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/postgres?sslmode=require
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=lax
ALLOWED_HOSTS=stockflow.example.com
TRUSTED_ORIGINS=https://stockflow.example.com
CORS_ORIGINS=https://stockflow.example.com
```

Keep proxy trust narrow with `PROXY_FORWARDED_ALLOW_IPS` (a proxy IP/CIDR). Trusting `*` is an
explicit platform decision and does not replace host validation. API documentation is disabled
by default in production; set `API_DOCS_ENABLED=true` only when intentionally exposing it.

## Release order

1. Configure the private production database URL and application settings.
2. From `backend`, run `alembic upgrade head`.
3. Run `python -m app.scripts.create_admin` and supply a unique password interactively.
4. Start the container/application. Check `/health`, `/ready`, login, and core workflows.

Schema migrations never run automatically at container startup. `/health` performs no database
access; `/ready` runs a sanitized `SELECT 1` check.

## Optional SQLite transfer

First migrate a fresh PostgreSQL target to head. Keep credentials in environment variables—not
command-line arguments:

```sh
export SOURCE_DATABASE_URL=sqlite:////absolute/path/to/stockflow.db
export TARGET_DATABASE_URL='postgresql+psycopg://...?...sslmode=require'
python -m app.scripts.migrate_database --dry-run
python -m app.scripts.migrate_database
```

The utility rejects a missing SQLite file, wrong revision, incomplete source, non-PostgreSQL or
non-fresh target, and unexpected expense categories. It derives FK order from reflected metadata,
copies and verifies counts inside one transaction, and rolls back on failure. It deliberately
excludes `user_sessions`, so everyone logs in again.

## Backups and recovery

Use `PGPASSWORD` supplied by a secret manager or a `.pgpass` file rather than embedding a password:

```sh
pg_dump --format=custom --file=stockflow.dump "$PRODUCTION_DATABASE_URL"
pg_restore --clean --if-exists --dbname="$RESTORE_TEST_DATABASE_URL" stockflow.dump
```

Regularly restore into an isolated database, run `alembic current`, check counts, `/ready`, login,
and representative reports. Protect and rotate backup files according to organizational policy.

## Destructive test separation

Production verification permits `alembic upgrade head`, probes, login, and application smoke tests.
Never run destructive migration pytest, downgrades, or `DROP SCHEMA` against Supabase production.
`TEST_POSTGRES_URL` must name a **different disposable database**, and destructive tests additionally
require `ALLOW_DESTRUCTIVE_POSTGRES_TESTS=true`.
