"""Small, inspectable confidence calibration helpers for the local reference app."""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

STOP = {"a", "an", "and", "are", "as", "at", "be", "by", "does", "for", "from", "how", "i", "in", "is", "it", "me", "my", "of", "on", "or", "the", "to", "what", "when", "where", "which", "who", "why", "with"}


def raw_support_score(question: str, status: str, evidence: list[dict]) -> float:
    """Return a heuristic support signal; it is not a probability until calibrated."""
    if status in {"refused", "denied"}:
        return 0.85
    if not evidence:
        return 0.05
    kinds = {item.get("kind") for item in evidence}
    if "tool_result" in kinds and any(item.get("verified") for item in evidence):
        return 0.92
    if "sql" in kinds:
        return 0.90
    terms = {x for x in re.findall(r"[a-z0-9]+", question.lower()) if len(x) > 2 and x not in STOP}
    excerpts = " ".join(str(item.get("excerpt", "")) for item in evidence).lower()
    body = set(re.findall(r"[a-z0-9]+", excerpts))
    overlap = len(terms & body) / max(1, len(terms))
    # Additional independent sources modestly increase support; cap keeps the
    # feature from treating duplicated evidence as certainty.
    source_count = len({item.get("source_id", item.get("id")) for item in evidence})
    return round(min(0.98, max(0.05, 0.12 + 0.68 * overlap + 0.04 * min(3, source_count - 1))), 6)


def fit_isotonic(samples: list[tuple[float, int]], version: str = "synthetic-isotonic-v1") -> dict:
    """Fit a monotone empirical mapping with Laplace smoothing and PAV."""
    if len(samples) < 4 or any(y not in (0, 1) or not math.isfinite(x) or not 0 <= x <= 1 for x, y in samples):
        raise ValueError("need at least four valid labeled confidence samples")
    grouped: dict[float, list[int]] = {}
    for score, label in samples:
        grouped.setdefault(float(score), []).append(int(label))
    blocks = []
    for x, labels in sorted(grouped.items()):
        # Beta(1,1) smoothing avoids declaring a finite sample perfectly certain.
        blocks.append({"lo": x, "hi": x, "n": len(labels), "success": sum(labels), "p": (sum(labels) + 1) / (len(labels) + 2)})
    i = 0
    while i < len(blocks) - 1:
        if blocks[i]["p"] <= blocks[i + 1]["p"]:
            i += 1
            continue
        left, right = blocks[i], blocks[i + 1]
        n = left["n"] + right["n"]
        success = left["success"] + right["success"]
        merged = {"lo": left["lo"], "hi": right["hi"], "n": n, "success": success, "p": (success + 1) / (n + 2)}
        blocks[i:i + 2] = [merged]
        i = max(0, i - 1)
    return {"version": version, "method": "isotonic_pav_beta_1_1", "n": len(samples), "bins": blocks}


def apply_calibrator(raw: float, artifact: dict | None) -> float:
    if not artifact or not artifact.get("bins"):
        return round(min(1.0, max(0.0, raw)), 4)
    for block in artifact["bins"]:
        if raw <= block["hi"]:
            return round(float(block["p"]), 4)
    return round(float(artifact["bins"][-1]["p"]), 4)


def choose_abstention_threshold(labels: list[int], predictions: list[float], target_accuracy: float = 0.8) -> float:
    """Choose the lowest train-set cutoff meeting a target selective accuracy."""
    if len(labels) != len(predictions) or not labels:
        raise ValueError("labels and predictions must be non-empty and equal length")
    for threshold in sorted(set(predictions)):
        kept = [label for label, probability in zip(labels, predictions) if probability >= threshold]
        if len(kept) >= 4 and sum(kept) / len(kept) >= target_accuracy:
            return round(float(threshold), 4)
    return 1.0


def calibration_metrics(labels: list[int], predictions: list[float], bins: int = 5) -> dict:
    if len(labels) != len(predictions) or not labels:
        raise ValueError("labels and predictions must be non-empty and equal length")
    brier = sum((p - y) ** 2 for y, p in zip(labels, predictions)) / len(labels)
    ece = 0.0
    details = []
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        indices = [j for j, p in enumerate(predictions) if lo <= p < hi or (i == bins - 1 and p == 1)]
        if not indices:
            continue
        mean_p = sum(predictions[j] for j in indices) / len(indices)
        accuracy = sum(labels[j] for j in indices) / len(indices)
        ece += len(indices) / len(labels) * abs(mean_p - accuracy)
        details.append({"range": [round(lo, 2), round(hi, 2)], "n": len(indices), "mean_confidence": round(mean_p, 4), "accuracy": round(accuracy, 4)})
    return {"n": len(labels), "brier_score": round(brier, 4), "expected_calibration_error": round(ece, 4), "bins": details}


def load_calibrator(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if value.get("bins") else None
    except (OSError, ValueError, AttributeError):
        return None
