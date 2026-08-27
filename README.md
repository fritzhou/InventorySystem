# StockFlow

StockFlow is a progressively built inventory and point-of-sale system for small retailers. This first milestone establishes a working React client, FastAPI REST API, SQLAlchemy data layer, PostgreSQL/Supabase configuration, and the first three relational models. POS, authentication, sales, and camera scanning are deliberately **not** implemented yet.

## Architecture

```text
Browser / device
  React UI + TypeScript types
       | HTTPS JSON (REST)
       v
  FastAPI + Pydantic validation
       | SQLAlchemy sessions and queries
       v
  Supabase-hosted PostgreSQL
```

- **React** composes the interface from reusable components. Hooks such as `useProducts` own request/loading/error state. A state change makes React update only the affected UI.
- **TypeScript** checks the frontend's data shapes before the app runs. `Product` describes the API response, catching many misspelled fields and incorrect value types during development.
- **REST** is the HTTP boundary between browser and server. The frontend calls `GET /api/products`; FastAPI returns JSON plus an HTTP status code. Later, camera scanning will happen in the browser and only its decoded barcode string will cross this same boundary.
- **FastAPI/Python** owns validation and business rules. FastAPI maps URLs to router functions and uses Pydantic schemas to validate incoming/outgoing data. The interactive API documentation is available at `/docs`.
- **Dependency injection** supplies one SQLAlchemy database session to each API request through `Depends(get_db)`. The route does not construct global sessions, and the dependency reliably closes each session.
- **SQLAlchemy** maps Python model objects to relational tables and generates parameterized SQL. Parameterization helps prevent SQL injection; database constraints remain the final integrity boundary.
- **PostgreSQL on Supabase** persists production data. Supabase supplies managed PostgreSQL now and can supply Auth in the authentication milestone. FastAPI—not the browser—uses the private database connection string.
- **Alembic migrations** version schema changes so development and hosted databases can be upgraded reproducibly with `alembic upgrade head`.
- **Camera scanner (future milestone)** will use ZXing in React to request a rear camera, decode retail barcodes locally, stop after one result, then request `/api/products/barcode/{barcode}`. It will never receive database credentials or directly alter stock.

This separation is a security boundary: browser code is visible and modifiable by users, so future price verification, sales transactions, stock deduction, and role authorization must live in FastAPI.

## Project structure

```text
frontend/src/
  components/     reusable presentation pieces
  pages/          screen-level composition
  services/       typed HTTP communication with FastAPI
  hooks/          reusable React state/effect behavior
  types/          TypeScript API contracts
  utils/          future pure helper functions
backend/app/
  core/            settings and cross-cutting configuration
  models/          SQLAlchemy table mappings
  schemas/         Pydantic request/response contracts
  routers/         REST endpoints grouped by resource
  services/        future multi-step business operations
  dependencies/    future auth and shared request dependencies
  database.py      engine, session factory, and declarative base
  main.py          FastAPI application assembly and middleware
backend/alembic/   versioned PostgreSQL schema migrations
backend/tests/     API integration tests using isolated SQLite
```

The frontend and backend have separate dependencies and deployments. Within each, folders separate presentation, transport, validation, persistence, and future business logic so features can grow without giant files.

## Initial data model

- `users.id`, `categories.id`, and `products.id` are UUID **primary keys**: stable unique row identities that are safer to expose than sequential counts.
- A product's `category_id` **foreign key** must point to an existing category. This is a one-to-many relationship: one category has many products, while each product belongs to one category. `RESTRICT` prevents deleting a category still referenced by products.
- Unique constraints/indexes prevent duplicate user emails, category names, SKUs, and non-null barcodes. Search/filter indexes improve lookups by name, category, active state, SKU, and barcode. Check constraints prohibit negative money and inventory values even if application validation is bypassed.
- Prices use PostgreSQL `NUMERIC(12,2)` and Python `Decimal`, not binary floating point. Decimal arithmetic represents currency amounts such as `0.10` exactly and prevents accumulating float rounding errors.
- Products are deactivated rather than deleted through the API. This prepares the system to preserve future sale and audit history.
- `users.role` is constrained to `admin` or `cashier`. It is only groundwork: endpoints are intentionally unauthenticated in this foundation and must not be exposed publicly until Supabase JWT verification and authorization are added.

## Data flow in this milestone

1. `ProductsPage` calls `useProducts` when React mounts it.
2. The hook calls the centralized `api.getProducts()` service, which sends `GET /api/products` to the URL in `VITE_API_URL`.
3. FastAPI's product router asks `get_db` for a request-scoped SQLAlchemy session.
4. SQLAlchemy sends a parameterized query through the Psycopg PostgreSQL driver.
5. FastAPI serializes model rows through `ProductRead`; the service parses the JSON into the TypeScript `Product[]` contract; React stores it in state and renders the table.
6. A network/server error becomes a clear retry-oriented message instead of crashing the page.

`async`/`await` and promises allow the browser to remain responsive while network I/O is pending. The hook's effect cleanup prevents a completed request from updating state after its component is removed.

## Environment and security

Copy `.env.example` to `.env` and replace the placeholders. A backend environment variable such as `DATABASE_URL` is **private** and remains only on the API host. A Vite variable prefixed with `VITE_` is **public** because Vite embeds it in downloadable JavaScript; only the public API base URL belongs there. Never place a database password, Supabase service-role key, private JWT key, or other secret in frontend variables or Git.

CORS only allows configured browser origins. CORS is not authentication: it helps browsers enforce origin rules, while the later JWT milestone will establish identity and roles. API schemas and database constraints already validate input, but product writes must be protected by role checks before production deployment.

## Local setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp ../.env.example .env  # then set the real Supabase DATABASE_URL
alembic upgrade head
uvicorn app.main:app --reload
```

For local exploration without Supabase, omit `backend/.env`; the configured development fallback is SQLite. Apply migrations before creating data. Visit `http://localhost:8000/health` and `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
cp ../.env.example .env
npm run dev
```

Open `http://localhost:5173`. The frontend default API URL is `http://localhost:8000`.

### Verification

```bash
cd backend && pytest
cd backend && ruff check .
cd frontend && npm test
cd frontend && npm run lint
cd frontend && npm run build
```
