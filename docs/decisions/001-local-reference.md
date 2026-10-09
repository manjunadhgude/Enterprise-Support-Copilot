# Decision 001: dependency-free local reference

- **Problem:** deliver a runnable demonstrator without installed services or model credentials.
- **Options:** PostgreSQL/vector DB and hosted LLM; an in-memory sketch; local SQLite and deterministic components.
- **Decision:** SQLite, Python stdlib HTTP server, an actually fitted Naive Bayes router, and deterministic response/tool logic.
- **Reasons:** the runtime has no FastAPI, scikit-learn, or model package; a dependency-free implementation can start locally and exercise meaningful data paths.
- **Trade-offs:** not production scalable; no neural retrieval or natural-language generation; identity is demonstrative; evaluation is weak due to tiny synthetic data.
- **Revisit when:** real deployment constraints, identity provider, data residency, load, and model provider are known.
