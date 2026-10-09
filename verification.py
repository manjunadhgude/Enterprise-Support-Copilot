"""Deterministic grounding checks for the local template-based answer paths."""
from __future__ import annotations

import re


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def verify_answer(answer: str, status: str, evidence: list[dict]) -> dict:
    checks = []
    if status in {"refused", "denied", "abstained", "error", "needs_approval"}:
        return {"passed": True, "method": "policy-or-abstention-state", "checks": [{"check": "non-answer-state", "passed": True}]}
    if status != "answered":
        return {"passed": False, "method": "deterministic-evidence-checks-v1", "checks": [{"check": "recognized-status", "passed": False}]}
    if not evidence:
        return {"passed": False, "method": "deterministic-evidence-checks-v1", "checks": [{"check": "evidence-present", "passed": False}]}

    kinds = {item.get("kind") for item in evidence}
    text = _norm(answer)
    if kinds == {"document"}:
        body = _norm(re.sub(r"^Based on the current authorized documentation:", "", answer, flags=re.I))
        supported = any(body and body in _norm(item.get("excerpt", "")) for item in evidence)
        checks.append({"check": "answer-text-is-authorized-document-excerpt", "passed": supported})
    elif "device_id" in text or any(item.get("device_id") for item in evidence):
        docs = [item for item in evidence if item.get("kind") == "document"]
        device_rows = [item for item in evidence if item.get("kind") == "sql" and isinstance(item.get("facts"), dict)]
        policy_text = _norm(" ".join(item.get("excerpt", "") for item in docs))
        device_ok = False
        if len(docs) and len(device_rows) == 1:
            row = device_rows[0]
            labels = {"company_owned": "company owned", "encrypted": "encrypted", "os_supported": "os supported", "endpoint_protection": "endpoint protection"}
            policy_anchors = ["manager approval", "multi factor authentication", "company managed", "endpoint protection"]
            policy_ok = all(anchor in policy_text for anchor in policy_anchors)
            values_ok = all((label in text and ("yes" if value else "no") in text) for key, value in row["facts"].items() for label in [labels[key]])
            expected_unmet = [labels[key] for key, value in row["facts"].items() if not value]
            requirement_ok = all(label in text for label in expected_unmet) and ("unmet recorded requirement" in text if expected_unmet else "all recorded device checks pass" in text)
            device_ok = policy_ok and values_ok and requirement_ok and _norm(row.get("device_id", "")) in text
        checks.append({"check": "device-comparison-matches-policy-and-sql-facts", "passed": device_ok})
    elif kinds == {"sql"}:
        row = evidence[0]
        if row.get("query_template") == "open_tickets_by_assignee":
            valid = str(row.get("value")) in text and _norm(str(row.get("assignee_id", ""))) in text and "open support ticket" in text
        else:
            valid = False
        checks.append({"check": "sql-answer-matches-approved-query-result", "passed": valid})
    elif "tool_result" in kinds:
        valid = True
        for item in evidence:
            if item.get("id") == "tool:service-status:vpn":
                valid = valid and item.get("status", "").lower() in text and item.get("service", "").lower() in text
            elif item.get("kind") == "tool_result" and "ticket_id" in item:
                valid = valid and str(item["ticket_id"]) in text and item.get("status", "").lower() in text and bool(item.get("verified"))
            else:
                valid = False
        checks.append({"check": "tool-answer-matches-verified-tool-result", "passed": valid})
    else:
        checks.append({"check": "supported-answer-type", "passed": False})
    return {"passed": bool(checks) and all(item["passed"] for item in checks), "method": "deterministic-evidence-checks-v1", "checks": checks}
