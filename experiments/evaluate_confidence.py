"""Measure a confidence calibrator against authored, executable synthetic QA cases."""
import json, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app
from confidence import apply_calibrator, calibration_metrics, choose_abstention_threshold, fit_isotonic, raw_support_score


def judged_correct(row, result):
    kinds = {item.get("kind") for item in result["evidence"]}
    return int(
        result["status"] == row["status"]
        and result["verification"]["passed"]
        and set(row["evidence_kinds"]).issubset(kinds)
        and all(term.lower() in result["answer"].lower() for term in row["answer_contains"])
    )


def main():
    rows = [json.loads(line) for line in (ROOT / "experiments" / "confidence_eval.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    original_db, original_model, original_loader = app.DB, app.MODEL, app.load_calibrator
    with tempfile.TemporaryDirectory(prefix="p1-confidence-eval-") as temp:
        app.DB = Path(temp) / "confidence.sqlite3"
        app.MODEL = Path(temp) / "router.json"
        # Evaluation observations must come from the raw system, not its previous fitted artifact.
        app.load_calibrator = lambda _path: None
        app.init_db()
        app.train_router()
        observed = []
        for row in rows:
            result = app.handle_question(row["query"], app.USERS[row["user"]])
            observed.append({"row": row, "raw": raw_support_score(row["query"], result["status"], result["evidence"]), "correct": judged_correct(row, result), "status": result["status"]})
    app.DB, app.MODEL, app.load_calibrator = original_db, original_model, original_loader

    train = [x for i, x in enumerate(observed) if i % 3 != 1]
    test = [x for i, x in enumerate(observed) if i % 3 == 1]
    calibrator = fit_isotonic([(x["raw"], x["correct"]) for x in train])
    train_probabilities = [apply_calibrator(x["raw"], calibrator) for x in train]
    threshold = choose_abstention_threshold([x["correct"] for x in train], train_probabilities)
    calibrator["abstention_threshold"] = threshold
    calibrator["threshold_selection"] = {"target_train_selective_accuracy": 0.8, "minimum_retained_train_cases": 4, "policy": "lowest threshold achieving target on the training split"}
    calibrated = [apply_calibrator(x["raw"], calibrator) for x in test]
    labels = [x["correct"] for x in test]
    raw_metrics = calibration_metrics(labels, [x["raw"] for x in test])
    calibrated_metrics = calibration_metrics(labels, calibrated)
    threshold_report = {}
    for threshold in (0.5, 0.6, 0.7, 0.8):
        kept = [(y, p) for y, p in zip(labels, calibrated) if p >= threshold]
        threshold_report[str(threshold)] = {"coverage": round(len(kept) / len(labels), 4), "selective_accuracy": round(sum(y for y, _ in kept) / len(kept), 4) if kept else None, "n_answered": len(kept)}
    report = {
        "dataset": "authored synthetic end-to-end support scenarios with executable expected-outcome assertions",
        "n_total": len(rows), "n_train": len(train), "n_test": len(test),
        "split": "fixed every-third holdout (index modulo 3 equals 1); do not tune on holdout",
        "raw_support_signal_test": raw_metrics, "calibrated_test": calibrated_metrics,
        "abstention_threshold_selected_on_train": calibrator["abstention_threshold"],
        "selective_coverage_accuracy": threshold_report,
        "calibrator": calibrator,
        "limitations": "Small, authored synthetic set from a deterministic demo application. The expected-outcome checks are narrow, examples are not independent production observations, and the holdout is too small for a production confidence or abstention claim. Rebuild calibration with representative reviewed outcomes before deployment.",
        "holdout_cases": [{"query": x["row"]["query"], "correct": x["correct"], "raw": x["raw"], "calibrated": p, "actual_status": x["status"]} for x, p in zip(test, calibrated)],
    }
    (ROOT / "models" / "confidence_calibrator.json").write_text(json.dumps(calibrator, indent=2), encoding="utf-8")
    (ROOT / "experiments" / "confidence_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# Confidence calibration experiment", "", f"Dataset: {report['dataset']}.", f"Train/test: {len(train)}/{len(test)} cases.", f"Abstention threshold selected on training data: {calibrator['abstention_threshold']:.4f}.", "", "| Metric | Raw signal | Calibrated |", "|---|---:|---:|", f"| Brier score (lower is better) | {raw_metrics['brier_score']:.4f} | {calibrated_metrics['brier_score']:.4f} |", f"| Expected calibration error (lower is better) | {raw_metrics['expected_calibration_error']:.4f} | {calibrated_metrics['expected_calibration_error']:.4f} |", "", "## Selective answer trade-off", "", "| Confidence threshold | Coverage | Accuracy among retained | Count |", "|---:|---:|---:|---:|"]
    for threshold, item in threshold_report.items():
        acc = "n/a" if item["selective_accuracy"] is None else f"{item['selective_accuracy']:.3f}"
        lines.append(f"| {threshold} | {item['coverage']:.3f} | {acc} | {item['n_answered']} |")
    lines += ["", report["limitations"]]
    (ROOT / "experiments" / "confidence_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("n_total", "n_train", "n_test", "raw_support_signal_test", "calibrated_test", "selective_coverage_accuracy", "limitations")}, indent=2))


if __name__ == "__main__":
    main()
