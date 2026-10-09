# P1 implementation status

Status is assessed against the supplied P1 master specification. “Implemented” means the behavior exists in this repository and has a local test or reproducible command; it does not imply production readiness.

**Current target:** the project owner selected a local-only demo. Cloud hosting, paid model API calls, live identity, and real enterprise IT integrations are optional and are not required for this target.

| Area | Status | Evidence / remaining work |
|---|---|---|
| Local application and interface | Partial | Responsive chat/evidence view and a role-aware approval interface are present. Document ingestion/list/deactivation and read-only evaluation reports are available to Admin. |
| Authentication and authorization | Partial | Local demo sessions and OIDC code+PKCE flow with tenant/role allowlist; OIDC tests use mocks. Basic in-process throttles exist, but no distributed protection; no live IdP certification, MFA lifecycle, or production identity policy. |
| Tenant and document ACL filtering | Implemented for local demo | Query-time tenant and role filtering; regression test covers tenant isolation. |
| Learned retrieval router | Implemented, limited evidence | Multinomial Naive Bayes trains from synthetic labels and runs at request time. Held-out accuracy is 0.75 on eight examples; this is not representative of field performance. |
| BM25, dense, hybrid and reranking research | Partial | BM25-style ranking, local TF-IDF cosine, and RRF are present. “Dense” is a lexical approximation; no neural embeddings or learned reranker. Six-query synthetic comparison now includes keyword, TF-IDF, hybrid, fixed-hybrid, and learned-router strategies; all tie on this tiny set, so it gives no evidence of superiority. No independent annotators or production relevance judgments. |
| Multi-hop and SQL | Partial | Deterministic mixed-evidence workflow and parameterized SQL templates exist. Decomposition is rule-based and limited to demo scenarios. |
| Document ingestion and lifecycle | Partial | Bounded TXT/Markdown/PDF/DOCX extraction, structural chunking, versions, retrieval deactivation, and a versioned SQLite schema migrations and categorized feedback are implemented. Synchronous only; no OCR, queue, external object store, or PostgreSQL migration track. |
| Tools and approvals | Partial | Mock service status, idempotent tickets, and dual-control, task-linked VPN revocation with persisted execution verification are tested. No live adapters are configured. |
| Structured answers, citations, claim verification | Partial | Responses expose evidence/trace fields and pass a versioned JSON Schema contract. Deterministic checks now verify current document excerpts, SQL values, tool results, and device facts, abstaining on mismatch. There is no semantic claim-entailment verifier for free-form generation. |
| Calibrated confidence and abstention | Partial | Isotonic calibration is fitted on 12 authored synthetic cases, evaluated on six held-out cases, and a training-selected threshold gates local answers. The measured pipeline is reproducible, but the sample and deterministic answer checks are too small for production confidence claims; needs representative independently reviewed outcomes. |
| State, audit, and recovery | Partial | SQLite task/audit state, request IDs, versioned route aliases, caller-scoped task reads, basic in-process throttles, and action idempotency exist. Synchronous cancellation is reported as unsupported; no worker queue, bounded retry framework, distributed recovery, or production retention/metrics. |
| Evaluation and experiments | Partial | Synthetic router holdout, six-query retrieval comparison, and 18-scenario confidence calibration experiment run reproducibly. No independent annotators, representative answer-quality evaluation, calibration study at production scale, security-rate suite, or rigorous ablations. |
| Tests, CI, container packaging | Partial | All 27 tests passed locally, including the two OIDC integration tests after installing pinned requirements into a temporary task-local dependency folder. All three synthetic evaluation scripts and Python compilation passed. GitHub Actions CI run #1 passed after push; every step including the Docker image build succeeded. See [workflow run #1](https://github.com/manjunadhgude/Enterprise-Support-Copilot/actions/runs/37972606616). Local Docker is unavailable. |
| Production deployment | Not implemented | No PostgreSQL/pgvector deployment, real secret manager, production monitoring, backup/restore, PostgreSQL migration track, or live provider validation. |
| Cost-conscious student path | Documented | Local-first use requires no cloud hosting or API calls. Optional Azure for Students deployment guidance covers usage limits, scale-to-zero, budget alerts, and deleting demo resources; actual eligibility and costs must be checked in the user's account. |

## Local verification performed

- `python -m unittest discover -s tests -v` — 27 tests succeeded; two optional OIDC integration tests skipped due to missing dependencies in the bundled runtime.
- `python experiments/evaluate.py` — regenerated the eight-example router report (6/8 correct, 0.75 accuracy).
- `python experiments/evaluate_retrieval.py` — compared keyword, TF-IDF, hybrid, fixed-hybrid, and learned-router retrieval using six hand-labeled synthetic queries; all scored Recall@3 1.0, Precision@3 0.5556, and MRR@3 1.0. Latency is only a local microbenchmark. See `experiments/retrieval_report.md` and `experiments/retrieval_report.json`.
- `python experiments/evaluate_confidence.py` — fitted isotonic calibration on 12 authored synthetic cases and evaluated six held-out cases; see `experiments/confidence_report.md` and `experiments/confidence_report.json`. A local threshold is selected on training data. The holdout is too small to claim production calibration.
- `python -m py_compile app.py confidence.py verification.py ingestion.py experiments/evaluate.py experiments/evaluate_retrieval.py experiments/evaluate_confidence.py` — passed.
- `docker --version` — unavailable in the current environment, so the Docker build remains unverified.

## Optional external setup for model-backed generation

No API key was created or saved because the local destination confirmation was declined. Since the selected target is a local-only demo, this is not a blocker: the deterministic workflow runs without an API key. If model-backed generation is wanted later, complete secure key provisioning and approve a local env-file destination first.

















