# Retrieval experiment report

Dataset: manual synthetic relevance judgments (6 queries, k=3).

| Strategy | Recall@3 | Precision@3 | MRR@3 | Mean latency (ms) |
|---|---:|---:|---:|---:|
| keyword | 1.0000 | 0.5556 | 1.0000 | 1.455 |
| dense | 1.0000 | 0.5556 | 1.0000 | 1.064 |
| hybrid | 1.0000 | 0.5556 | 1.0000 | 1.024 |
| fixed_hybrid | 1.0000 | 0.5556 | 1.0000 | 1.019 |
| learned_router | 1.0000 | 0.5556 | 1.0000 | 1.039 |

Six authored questions over five synthetic documents; no independent annotators, confidence intervals, production traffic, or generalization claim. Learned routing was trained on the separate small synthetic router set; non-document route predictions fall back to hybrid.
These measurements are a local pipeline check only. They do not establish that one retriever is better; the tiny authored test set yields identical ranking metrics across the three strategies.
