"""Reproducible evaluation of the detectors.   Run:  python evaluate.py [output.md]

1. PII detector - labelled texts in evaluation/pii_testset.json
   (matched per text at the level of "which finding TYPES were reported").
2. Risky-post ML model
   - 5-fold cross-validation on the training CSV (pipeline is re-fitted inside
     every fold, so the TF-IDF vocabulary never sees the test fold)
   - held-out set evaluation/holdout_posts.csv (never used for training or tuning)
Results are printed and written to evaluation/RESULTS.md (or the path given).
"""
import json
import os
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import StratifiedKFold, cross_val_predict

from app.services.pii_detector import detect_pii
from app.services.text_risk_model import DATA_PATH, build_pipeline

HERE = Path(__file__).resolve().parent
EVAL_DIR = HERE / "evaluation"
SEED = 42


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return p, r, f


def evaluate_pii(lines, filename, title):
    cases = json.loads((EVAL_DIR / filename).read_text(encoding="utf-8"))
    per_type = defaultdict(lambda: [0, 0, 0])   # tp, fp, fn
    misses, false_alarms = [], []
    exact_ok = 0

    for case in cases:
        expected = set(case["expected"])
        found = {f.type for f in detect_pii(case["text"])}
        for t in expected & found:
            per_type[t][0] += 1
        for t in found - expected:
            per_type[t][1] += 1
            false_alarms.append((case["text"], t))
        for t in expected - found:
            per_type[t][2] += 1
            misses.append((case["text"], t))
        exact_ok += expected == found

    tp = sum(v[0] for v in per_type.values())
    fp = sum(v[1] for v in per_type.values())
    fn = sum(v[2] for v in per_type.values())
    p, r, f = prf(tp, fp, fn)

    lines += [f"## {title}", "",
              f"{len(cases)} labelled texts. A finding counts as correct when its *type* was expected for that text.", "",
              f"**Overall: precision {p:.2f}, recall {r:.2f}, F1 {f:.2f}** "
              f"(TP {tp}, FP {fp}, FN {fn}); texts with exactly the right set of types: {exact_ok}/{len(cases)}", "",
              "| Type | TP | FP | FN | Precision | Recall | F1 |", "|---|---|---|---|---|---|---|"]
    for t, (a, b, c) in sorted(per_type.items()):
        pp, rr, ff = prf(a, b, c)
        lines.append(f"| {t} | {a} | {b} | {c} | {pp:.2f} | {rr:.2f} | {ff:.2f} |")
    lines += ["", "**Missed (false negatives):**", ""]
    lines += [f"- `{t}` -> {k}" for t, k in misses] or ["- none"]
    lines += ["", "**False alarms (false positives):**", ""]
    lines += [f"- `{t}` -> {k}" for t, k in false_alarms] or ["- none"]
    lines.append("")
    return {"precision": p, "recall": r, "f1": f}


def evaluate_ml(lines):
    df = pd.read_csv(DATA_PATH)
    hold = pd.read_csv(EVAL_DIR / "holdout_posts.csv")
    overlap = set(df.text.str.lower().str.strip()) & set(hold.text.str.lower().str.strip())
    dupes = int(df.text.str.lower().str.strip().duplicated().sum())

    lines += ["## 2. Risky-post ML model", "",
              f"Training set: {len(df)} posts ({int((df.label == 1).sum())} risky / {int((df.label == 0).sum())} safe), "
              f"duplicates: {dupes}. Held-out set: {len(hold)} posts, overlap with training: {len(overlap)}.", ""]

    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    cv_pred = cross_val_predict(build_pipeline(), df.text, df.label, cv=folds)
    p, r, f, _ = precision_recall_fscore_support(df.label, cv_pred, average="binary")
    tn, fp, fn, tp = confusion_matrix(df.label, cv_pred).ravel()
    lines += ["### 5-fold cross-validation (training CSV)", "",
              f"Precision {p:.2f}, recall {r:.2f}, F1 {f:.2f}. Confusion matrix: TN {tn}, FP {fp}, FN {fn}, TP {tp}.", ""]

    model = build_pipeline().fit(df.text, df.label)
    h_pred = model.predict(hold.text)
    hp, hr, hf, _ = precision_recall_fscore_support(hold.label, h_pred, average="binary")
    htn, hfp, hfn, htp = confusion_matrix(hold.label, h_pred).ravel()
    lines += ["### Held-out set (never used for training or tuning)", "",
              f"**Precision {hp:.2f}, recall {hr:.2f}, F1 {hf:.2f}**, accuracy {(h_pred == hold.label).mean():.2%}. "
              f"Confusion matrix: TN {htn}, FP {hfp}, FN {hfn}, TP {htp}.", "",
              "```", classification_report(hold.label, h_pred, target_names=["safe", "risky"], digits=2).strip(), "```", "",
              "**Held-out errors:**", ""]
    for text, label, pred in zip(hold.text, hold.label, h_pred):
        if label != pred:
            lines.append(f"- {'FN (missed risky)' if label == 1 else 'FP (false alarm)'}: {text}")
    lines += ["",
              "> Preliminary results on a small educational dataset. They show the approach works on posts written "
              "in the same style; they are **not** proof of reliability on the wider internet.", ""]
    return {"cv_f1": f, "holdout_precision": hp, "holdout_recall": hr, "holdout_f1": hf}


def evaluate_scenarios(lines):
    """Run realistic personas through the real API (network replaced by fixed data)."""
    os.environ["RATE_LIMIT_PER_MIN"] = "1000"
    from fastapi.testclient import TestClient
    from app.main import app
    from evaluation.scenarios import SCENARIOS, run_scenario

    lines += ["## 3. Risk score scenarios", "",
              "Expected levels were decided from the design of the formula before running. "
              "Network checks are replaced by fixed data so the table is reproducible.", "",
              "| Scenario | Expected | Score | Level | Match |", "|---|---|---|---|---|"]
    matches = 0
    with TestClient(app) as client:
        for sc in SCENARIOS:
            result = run_scenario(client, sc)
            ok = result["level"] == sc["level"]
            matches += ok
            lines.append(f"| {sc['name']} | {sc['level']} | {result['score']} | {result['level']} | {'yes' if ok else '**NO**'} |")
    lines += ["", f"{matches}/{len(SCENARIOS)} scenarios in the expected level.", ""]
    return {"scenarios_ok": matches, "scenarios": len(SCENARIOS)}


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else EVAL_DIR / "RESULTS.md"
    lines = ["# Evaluation results", "", f"Generated {date.today():%d %b %Y} by `python evaluate.py` (seed {SEED}).", ""]
    dev = evaluate_pii(lines, "pii_testset.json", "1a. PII detector - development set (rules were tuned on these)")
    unseen = evaluate_pii(lines, "pii_unseen.json", "1b. PII detector - unseen set (written without looking at the detector)")
    final = evaluate_pii(lines, "pii_final.json", "1c. PII detector - final test set (run once, never tuned on)")
    ml = evaluate_ml(lines)
    scen = evaluate_scenarios(lines)
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\nSaved to {out}")
    print("SUMMARY", json.dumps({"dev_f1": dev["f1"], "unseen": unseen, "final": final, **ml, **scen}, default=float))


if __name__ == "__main__":
    main()
