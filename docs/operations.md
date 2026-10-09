# Operations guide

1. Install Python 3.11+ and dependencies with `python -m pip install -r requirements.txt`.
2. Run `python app.py` from this directory.
3. Visit `http://127.0.0.1:8000`; stop with Ctrl+C. Liveness and readiness are available at `/health/live` and `/health/ready`; supported APIs also accept `/api/v1/` paths. Task reads are caller-scoped; pending approvals are linked to task IDs and can be approved through `/api/v1/tasks/{task_id}/approve`. Supported routes also use the `/api/v1/` prefix. Feedback may be categorized as helpful, incorrect, missing evidence, wrong citation, unsafe response, or other.
4. The SQLite file defaults to `platform.sqlite3` in this directory. Set `PLATFORM_DB` to a different path before startup to keep demo state elsewhere. Back it up only while the service is stopped.
5. Startup seeds only missing example rows and rewrites the router artifact from the checked-in synthetic training data.
6. Run `python -m unittest discover -s tests -v`, `python experiments/evaluate.py`, `python experiments/evaluate_retrieval.py`, and `python experiments/evaluate_confidence.py` to check behavior and regenerate all synthetic reports and the local confidence calibrator artifact. Review the limitations in each report before using the calibrator; it is not fit for production.
7. In the Admin document panel or with `POST /api/admin/documents`, submit text or a base64-encoded supported file (`.txt`, `.md`, `.pdf`, `.docx`). Parsers have byte/page/archive bounds; scanned PDF OCR is not supported. Check `GET /api/admin/ingestion/{job_id}` and list documents with `GET /api/admin/documents`. `POST /api/admin/delete-document` deactivates current chunks so retrieval stops returning them. ACLs are checked on each retrieval.
8. Inspect authorized audit events at `GET /api/audit` as Admin. Task history is available at `GET /api/tasks` for the authenticated demo identity. Support/Admin can initiate a VPN access revocation from the approval panel; a distinct Approver can approve and execute it or reject it.

For container use, run `docker compose up --build`; the Compose configuration persists SQLite in the `platform-data` volume and publishes only to loopback. To discard that demo database, stop the service and run `docker compose down --volumes`.

The Docker configuration was added but could not be built in this environment because Docker is not installed. The SQLite schema has a versioned migration ledger for local upgrades; it is not a production migration system for PostgreSQL. There is no production deploy, real secrets rotation, model promotion lifecycle, or backup/restore automation in this reference. Do not put real records or credentials in it.

## Optional OIDC setup

Install the pinned packages in `requirements.txt`, register the callback URI exactly, then set `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_REDIRECT_URI`, and `OIDC_SUBJECT_MAP` as shown in the README. Set `P1_LOCAL_AUTH_ENABLED=false` to disable local-password authentication; already-issued local sessions are rejected immediately. Store secrets outside source control. A provider-specific setup may need scopes or claim-map changes, but do not relax issuer, audience, state, nonce, signature, or TLS validation.










