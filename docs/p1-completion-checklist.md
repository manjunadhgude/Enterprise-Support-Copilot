# P1 project completion checklist

This checklist reflects the repository as verified on 2026-10-09. “Complete” means implemented and locally verifiable; it does not imply production readiness.

## Completed in this reference build

- [x] Scope chosen: local-only demo; no cloud hosting or paid model API is required for the demo.
- [x] Local server startup smoke check: `/health/live` returned `ok` and `/health/ready` returned `ready` using a temporary SQLite database.
- [x] Local Python HTTP app, browser UI, synthetic enterprise IT data, and SQLite persistence.
- [x] Local demo login/session handling, role checks, tenant filtering, CSRF protection, and OIDC authorization-code + PKCE implementation with mocked tests.
- [x] Trained Naive Bayes request router with reproducible synthetic holdout evaluation (6/8 correct; 0.75 accuracy).
- [x] BM25-style lexical retrieval, TF-IDF cosine approximation, reciprocal-rank hybrid retrieval, and overlap reranking.
- [x] Retrieval experiment comparing keyword, TF-IDF, hybrid, fixed-hybrid, and learned-router strategies on six manually judged synthetic queries. They tie on this data; it does not establish a winning strategy.
- [x] TXT, Markdown, PDF, and DOCX ingestion; structural chunking, document versions, retrieval deactivation, and categorized feedback.
- [x] Parameterized SQL templates, deterministic multi-step workflow, mock service lookup, and idempotent mock ticket creation.
- [x] Approval-gated mock VPN revocation with separate approver, fresh authorization checks, task linkage, and persisted-result verification.
- [x] Versioned response JSON Schema with runtime shape validation, evidence references, audit records, request IDs, health/readiness routes, and API v1 aliases.
- [x] Deterministic evidence checks for the current document, SQL, tool, and device response templates; failed checks cause abstention and are included in the response record.
- [x] Locally fitted isotonic confidence mapping, training-selected abstention threshold, and executable synthetic held-out calibration report.
- [x] SQLite schema migrations, caller-scoped task reads, bounded request bodies, and basic in-memory rate limits.
- [x] Admin UI for ingestion and viewing evaluation reports; operations, architecture, data-card, router-card, confidence-calibrator-card, decision, and completion-matrix documentation.
- [x] CI workflow, Dockerfile/Compose packaging, and local automated test suite.
- [x] Student-friendly cost plan documenting local-first development, optional Azure student credits, scale-to-zero hosting, budget-alert limits, and secret/database exclusions from Git.
- [x] Git ignore rules for local environment files, credentials, databases, and generated local files.

## Optional work beyond the chosen local-only demo

The local reference demo can run without these items. They remain incomplete only if the goal later changes to a full production deployment or model-backed product.

### Optional model-backed generation (uses an external API)

- [ ] Complete secure OpenAI API key provisioning and approve a local environment-file destination. The platform connection was reconnected, but the local destination confirmation was declined, so no key was created or written. Never paste the secret into chat or commit it.
- [ ] Implement provider-backed generation with timeout, retry, error handling, configuration, and safe fallback behavior; add mocked provider tests.
- [ ] Run an authorized live smoke test with the provisioned credential and record model/configuration and results without recording the secret.

### Optional research and production-quality evaluation

- [ ] Add a representative, independently reviewed retrieval/answer evaluation set; report confidence intervals and compare strategies across enough queries to support conclusions.
- [ ] Replace TF-IDF approximation with a selected embedding model/vector index if required by the P1 target; evaluate a learned reranker against the baseline.
- [ ] Replace the small authored calibration scenarios with a representative, independently reviewed answer-correctness set; re-fit and evaluate confidence calibration and abstention thresholds before production use.
- [ ] Add semantic claim-level evidence entailment verification for free-form model-generated answers; current deterministic checks cover only the template paths.
- [ ] Expand security, abuse, tenant-isolation, failure, and load testing beyond the current local test coverage.

### Out of scope for the selected local-only demo: production deployment and live integrations

- [ ] Replace SQLite with the target PostgreSQL/vector-store deployment and provide/test a migration path.
- [ ] Move synchronous ingestion and long-running tasks to a durable worker queue; implement real cancellation, bounded retries, idempotent recovery, and dead-letter handling.
- [ ] Replace in-memory rate limits with shared distributed controls; configure production identity, MFA/session policy, and validate OIDC against the selected live IdP.
- [ ] Add production secret management, TLS/deployment configuration, backup/restore drills, retention controls, structured metrics/logging/tracing, alerts, and operational runbooks.
- [ ] Implement and test approved live service/ticket/access adapters, with least-privilege credentials and approval/audit controls.
- [ ] Build and run the container in an environment with Docker, then execute deployment smoke and recovery checks.

## Verification snapshot

- Unit/integration suite: all 27 tests passed, including both OIDC integration tests after installing the pinned requirements into a temporary task-local dependency folder.
- Router evaluation: 8 synthetic holdout examples; 0.75 accuracy.
- Retrieval evaluation: 6 synthetic questions; all five strategies tied (Recall@3 1.0, Precision@3 0.5556, MRR@3 1.0).
- Confidence evaluation: 18 authored synthetic cases (12 train/6 holdout); holdout Brier score 0.0359 and ECE 0.1889 after calibration, versus raw-signal Brier 0.2303 and ECE 0.3720. These tiny-set measurements are not production evidence.
- GitHub Actions CI run #1 passed on the public repository after the push. Tests, all three evaluations, Python compilation, and the Docker image build succeeded. See [workflow run #1](https://github.com/manjunadhgude/Enterprise-Support-Copilot/actions/runs/37972606616).
- Docker image build: passed on the GitHub Actions runner. Docker remains unavailable locally and is not needed to run the selected local demo.
- Provider-backed generation: not implemented; secure API key provisioning is pending local destination approval. Deterministic local behavior remains available without API spend.
- Python module compilation and response JSON Schema parsing: passed.
- Local HTTP smoke check: `/health/live` returned `ok`; `/health/ready` returned `ready`.

Run from the repository root:

```powershell
python -m unittest discover -s tests -v
python experiments/evaluate.py
python experiments/evaluate_retrieval.py
python experiments/evaluate_confidence.py
python -m py_compile app.py confidence.py verification.py ingestion.py experiments/evaluate.py experiments/evaluate_retrieval.py experiments/evaluate_confidence.py
docker build -t p1-agentic-platform:local .
```
