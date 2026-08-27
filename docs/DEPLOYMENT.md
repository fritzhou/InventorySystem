# StockFlow production deployment

StockFlow uses **Supabase only as hosted PostgreSQL**. FastAPI/SQLAlchemy remains the sole database access layer and the existing `users` and `user_sessions` tables remain the authentication system. `DATABASE_URL` is server-side: the browser needs no Supabase anon key, service-role key, project ID, or database credential.

## 1. Prepare PostgreSQL and configuration

1. Create a Supabase project (or other PostgreSQL database) and obtain its server-side connection URI. Select a direct or transaction-pooler connection appropriate to the host. URL-encode special password characters and require TLS with `sslmode=require`.
2. Store the URI in the deployment platform's secret manager, never in Git. `postgres://` and `postgresql://` inputs are normalized to the SQLAlchemy psycopg driver.
3. Configure the container:

```dotenv
APP_ENV=production
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/postgres?sslmode=require
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_SAMESITE=lax
SESSION_COOKIE_NAME=stockflow_session
SESSION_EXPIRATION_HOURS=12
ALLOWED_HOSTS=stockflow.example.com
CORS_ORIGINS=https://stockflow.example.com
TRUSTED_ORIGINS=https://stockflow.example.com
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=2
DB_POOL_TIMEOUT=30
```

Use real values only in the provider's private environment. Production validation rejects SQLite, insecure cookies, wildcard hosts/CORS, and invalid origins. API docs are off by default. Serve HTTPS at one origin: `/` is React and `/api/*` is FastAPI. Leave `VITE_API_URL` unset at build time so the preserved empty-base URL behavior targets the same origin.

## 2. Initialize and deploy

Run these as explicit release/pre-deploy tasks from `/app` (migrations never run on API requests):

```bash
alembic upgrade head
python -m app.scripts.create_admin
```

The admin command prompts for credentials and creates no default password. Then build and deploy the provider-neutral image:

```bash
docker build -t stockflow:phase12 .
docker run --rm -p 8000:8000 --env-file /secure/path/stockflow.env stockflow:phase12
```

The image runs as a non-root user, serves the compiled SPA, honors `PORT`, and expects TLS termination by the hosting platform. Do not expose the service directly over plaintext production HTTP.

Verify `GET /health` returns liveness and `GET /ready` returns database readiness. Then log in and smoke-test dashboard, POS checkout, products, sales/returns, purchasing/receiving, expenses, users, audit log, refresh, logout, and direct navigation to React routes. API misses such as `/api/nonexistent` must remain JSON 404 responses.

## 3. Optional existing SQLite data transfer

First back up the source. The target must be a new database whose only rows are migration seeds and whose schema is already at Alembic head. From `backend`, keep both URLs private:

```bash
export SOURCE_DATABASE_URL='sqlite:////private/path/stockflow.db'
export TARGET_DATABASE_URL="$DATABASE_URL"
python -m app.scripts.migrate_database --dry-run
python -m app.scripts.migrate_database
```

The transactional utility derives foreign-key order from SQLAlchemy metadata, replaces only fresh migration-seeded expense categories, preserves identifiers/timestamps/Decimal values and historical/audit data, and verifies per-table counts. It refuses populated targets and never copies `alembic_version` or `user_sessions`; everyone must log in again. It prints counts, not row data, hashes, or URLs. Never point it at an established production database.

Expired/revoked sessions can later be removed safely with `python -m app.scripts.cleanup_sessions`.

## 4. Backups and recovery

Use provider-managed credentials or `PGPASSFILE`; never put a password in shell history or a committed command:

```bash
pg_dump --format=custom --no-owner --file=stockflow-$(date +%F).dump "$DATABASE_URL"
createdb stockflow_restore_test
pg_restore --no-owner --dbname="$RESTORE_DATABASE_URL" stockflow-YYYY-MM-DD.dump
```

Restrict and encrypt backup files. Regularly restore into an isolated database, run `alembic upgrade head`, compare critical counts, and perform application smoke tests. Establish retention and recovery objectives appropriate to the business; do not assume provider backups replace tested logical backups.

## 5. Manual Supabase verification in Codespaces

Set `DATABASE_URL` as a Codespaces secret, open a fresh terminal, and run from `backend`:

```bash
APP_ENV=development alembic upgrade head
TEST_POSTGRES_URL="$DATABASE_URL" python -m pytest -q tests/test_postgres_migrations.py
```

The test is destructive and **must only use a dedicated empty test database**, never a production Supabase database. Run the full test suites afterward. Unset secrets when finished and confirm no `.env` was staged.

Local development remains unchanged: SQLite defaults for FastAPI on port 8000 and Vite on port 5173 with its development proxy.
