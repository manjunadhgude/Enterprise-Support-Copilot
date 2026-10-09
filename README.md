# Production Agentic AI Engineering Platform

**Adaptive Enterprise Knowledge & Support Copilot** — a runnable, local reference implementation using synthetic IT data.

## Run locally

Requires Python 3.11 or later. The app uses pinned dependencies for OIDC and document parsing.

```powershell
python -m pip install -r requirements.txt
python app.py
```

To enable organization sign-in, register `http://localhost:8000/auth/oidc/callback` as the exact callback URL at your OIDC provider, install the pinned packages with `python -m pip install -r requirements.txt`, then configure these environment variables before starting the app:

```powershell
$env:OIDC_ISSUER = "https://your-idp.example/tenant"
$env:OIDC_CLIENT_ID = "your-client-id"
$env:OIDC_CLIENT_SECRET = "<from your secret manager>"
$env:OIDC_REDIRECT_URI = "http://localhost:8000/auth/oidc/callback"
$env:OIDC_SUBJECT_MAP = '{"stable-idp-subject":{"id":"E-1042","tenant":"acme","role":"employee"}}'
$env:P1_LOCAL_AUTH_ENABLED = "false"
python app.py
```

`OIDC_SUBJECT_MAP` is an app-owned allowlist keyed by the exact OIDC `sub` claim. Roles and tenant are sourced from this server-side map, never accepted from the browser or untrusted request parameters. Use an HTTPS callback outside localhost; the app sets `Secure` cookies automatically when the configured redirect URI uses HTTPS. Store the client secret in your deployment secret manager. No provider credentials are included here.

Open <http://127.0.0.1:8000> for the local demo. If you configure OIDC, browse to <http://localhost:8000> so the hostname matches the registered localhost callback. The app initializes a local SQLite database, seeds synthetic knowledge/operational records, and trains the Naive Bayes router artifact at startup. Sign in as `employee`, `support`, `admin`, `approver`, or `other`; all use `P1_DEMO_PASSWORD`, default `demo-pass-change-me`. Set that environment variable before startup to change the shared local demo password. Sessions use random opaque HttpOnly/SameSite cookies, server-side expiry, PBKDF2 password hashes, and CSRF tokens. The single-process demo has basic in-memory sign-in and per-user question rate limits; they reset on restart and are not production distributed controls. This is a local demonstration account system, not a replacement for an enterprise identity provider.

```powershell
python -m unittest discover -s tests -v
python experiments/evaluate.py
python experiments/evaluate_retrieval.py
python experiments/evaluate_confidence.py
```

### Container run

Docker Compose builds the app and persists its SQLite database in a named volume. The listener is bound to localhost.

```powershell
docker compose up --build
```

The GitHub Actions workflow installs the pinned dependencies, runs the unit/integration suite, regenerates synthetic router, retrieval, and confidence reports, compiles the Python modules, and builds the Docker image on pushes and pull requests.

Set `PORT` or `PLATFORM_DB` to configure the listener or database path. The server binds to loopback by default. No external model credentials are needed.

## What works in this reference build

- Local HTTP application and responsive chat/evidence UI.
- Synthetic users, documents, devices, tickets, and service state in SQLite.
- Tenant + role checks at request and retrieval time; parsed TXT/Markdown/PDF/DOCX ingestion, structural chunking, version history, deletion propagation, categorized feedback and audit records.
- A trained multinomial Naive Bayes retrieval router with a persisted JSON artifact; BM25-like lexical ranking, TF-IDF cosine semantic approximation, hybrid reciprocal-rank fusion, and overlap reranking.
- Strict, parameterized SQL templates for ticket counts and device inventory; no model-generated SQL.
- Explicit deterministic mixed-evidence workflow with subquestions/dependency trace.
- Read-only service check and idempotent mock ticket creation; result IDs are verified from SQLite.
- Refusal for secret requests, role-aware cross-employee ticket lookup, approval request/decision API, task state, feedback, and trace output.
- A documented, versioned JSON response contract (`schemas/response.schema.json`) validated at runtime.
- A fitted isotonic confidence mapper and training-selected answer threshold, with a reproducible 18-case synthetic end-to-end experiment and held-out Brier/ECE report. This demonstrates the calibration pipeline only; it is not reliable for production.
- Deterministic evidence checks for document-excerpt, approved SQL, tool-result, and device-comparison answer paths; a failed check produces an abstention and is recorded in the response verification record.
- A dual-control mock VPN access-revocation workflow with reauthorization, persisted execution result, and result verification; role-aware admin ingestion and approval controls are available in the UI.
- Schema-validated response records with a versioned contract.
- Twenty-seven unit/integration tests, a small router holdout, synthetic relevance-labeled retrieval comparison, confidence calibration report, and deterministic grounding checks.

Example endpoints: GET `/health/live`, GET `/health/ready`, GET `/api/health`, GET `/api/v1/tasks/{task_id}`, versioned `/api/v1/*` aliases for supported routes, GET `/api/me`, GET `/api/documents`, POST `/api/chat`, POST `/api/feedback`, admin POST `/api/admin/documents` (text or base64 file), GET `/api/admin/documents`, GET `/api/admin/ingestion/{job_id}`, POST `/api/admin/delete-document`, Admin GET `/api/admin/evaluation`, GET `/api/approvals`, support/admin POST `/api/approvals/request` (VPN revocation), and approver POST `/api/approvals/decide` (approve and execute or reject).

Authentication endpoints: `POST /api/login`, `GET /api/csrf`, `POST /api/logout`. Authenticated mutations require the session cookie and `X-CSRF-Token` returned at login or by `/api/csrf`.

OIDC uses authorization code flow with PKCE S256, one-time server-side state and nonce, strict issuer/discovery checks, HTTPS endpoints, JWK signature verification and `iss`/`aud`/`exp`/`iat`/`nonce` validation. `GET /auth/oidc/start` begins the redirect; `/auth/oidc/callback` exchanges the one-time code and creates an app session only for allowlisted subjects. Authlib's documented HTTP client supports persisted `state`, authorization-code exchange, PKCE and OIDC token handling; the implementation pins Authlib 1.8.0 and joserfc for the signed-token path ([Authlib HTTP client docs](https://docs.authlib.org/en/stable/oauth2/client/http/index.html), [joserfc JWT validation](https://jose.authlib.org/en/guide/jwt/)).

## Architecture

```text
Browser → local HTTP API → demo identity / tenant-role policy
                         → deterministic workflow planner
                         → learned strategy router → lexical / TF-IDF / hybrid retrieval
                         → approved parameterized SQL / mock service and ticket tools
                         → evidence references + task state + audit + feedback
```

See [architecture and limitations](docs/architecture.md), [operations](docs/operations.md), [data card](docs/data-card.md), [router model card](docs/router-model-card.md), [confidence calibrator card](docs/confidence-calibrator-card.md), [P1 implementation status](docs/p1-completion-matrix.md), and [decision record](docs/decisions/001-local-reference.md).

## Low-cost student path

The project runs locally with synthetic data and does not require cloud hosting or model API usage. See the [student-friendly low-cost plan](docs/student-low-cost-plan.md) before provisioning cloud services. The `.gitignore` excludes local env files, credentials, and SQLite databases from Git.

## Important limitations and unfinished specification items

This is a runnable local engineering reference, **not a production-ready deployment or a claim that every P1 requirement is complete**. OIDC is covered with mock integration tests, but has not been tested against a live provider because no provider credentials or subject mapping were supplied. SQLite is used instead of PostgreSQL/pgvector, and ingestion runs synchronously without a background queue. Search uses BM25-style lexical scoring and a local TF-IDF semantic approximation; there is no neural embedding or learned reranker. No external generation model is configured, so synthesis is deterministic template logic. Deterministic grounding checks cover the current answer templates; there is no semantic claim-entailment verifier for free-form generated claims. Confidence now has a locally fitted isotonic mapping and train-selected abstention threshold, but its 18 authored synthetic scenarios and six-case holdout are far too small to support production confidence claims. Router and retrieval reports also use small synthetic datasets; retrieval judgments are authored for the demo and are not independent or representative. Local accounts share a demo password and must not be used for sensitive data. A local dual-control VPN revocation mock is approval-gated, but there are no live operational adapters. CI and container packaging are provided; no live enterprise connector, production secret store, PostgreSQL deployment, or provider certification is included. Reports are in `experiments/`. See the architecture and operations docs for remaining limits.

This build reports measured results on small synthetic router, retrieval, and confidence datasets only; it does not claim enterprise accuracy, production-ready calibration, production readiness, or completion of all Definition of Done items.



















