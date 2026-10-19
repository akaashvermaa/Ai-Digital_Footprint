"""Machine-learning model that flags risky posts.

Pipeline: TF-IDF on character n-grams (turns text into numbers; 2-5 letter
          chunks also handle typos and word forms like "travel"/"travelling")
          -> Logistic Regression (learns which patterns signal risk).
Character n-grams scored ~92% in 5-fold cross-validation vs ~85% for word n-grams.
Trained on app/data/training_posts.csv (label 1 = risky, 0 = safe).
"""
import re
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline

from app.schemas import Finding
from app.services.explanations import describe
from app.services.pii_detector import redact
from app.services.risk_scorer import content_breakdown

APP_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = APP_DIR / "data" / "training_posts.csv"
MODEL_PATH = APP_DIR / "models" / "risk_model.joblib"

RISKY_THRESHOLD = 0.6  # a sentence above this probability is reported

_model = None


def build_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=1000, C=10, class_weight="balanced")),
    ])


def train(verbose: bool = False) -> dict:
    """Train on the CSV, print test accuracy, then retrain on all data and save."""
    df = pd.read_csv(DATA_PATH)
    x_train, x_test, y_train, y_test = train_test_split(
        df["text"], df["label"], test_size=0.2, random_state=42, stratify=df["label"])

    pipe = build_pipeline().fit(x_train, y_train)
    predictions = pipe.predict(x_test)
    accuracy = accuracy_score(y_test, predictions)
    if verbose:
        folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(build_pipeline(), df["text"], df["label"], cv=folds)
        print(f"Training samples: {len(x_train)}, test samples: {len(x_test)}")
        print(f"Test accuracy (80/20 split): {accuracy:.2%}")
        print(f"5-fold cross-validation accuracy: {cv_scores.mean():.2%}\n")
        print(classification_report(y_test, predictions, target_names=["safe", "risky"]))

    final = build_pipeline().fit(df["text"], df["label"])
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(final, MODEL_PATH)
    return {"accuracy": accuracy, "samples": len(df)}


def get_model() -> Pipeline:
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            train()
        _model = joblib.load(MODEL_PATH)
    return _model


def split_sentences(text: str) -> list[str]:
    return [t for t, _ in _sentences_with_offsets(text)]


def _sentences_with_offsets(text: str) -> list[tuple[str, int]]:
    out = []
    for m in re.finditer(r"[^.!?\n]+[.!?]*", text):
        sentence = m.group().strip()
        if len(sentence) > 3:
            out.append((sentence, m.start() + (len(m.group()) - len(m.group().lstrip()))))
    return out


def _explained_by_pii(sentence: str, start: int, covered: list[tuple[int, int]]) -> bool:
    """True if, once the personal info found in this sentence is removed, almost nothing is left."""
    chars = list(sentence)
    removed = False
    for a, b in covered:
        for i in range(max(a, start), min(b, start + len(sentence))):
            chars[i - start] = " "
            removed = True
    leftover = re.findall(r"[A-Za-z]{3,}", "".join(chars))
    return removed and len(leftover) < 3


def analyze_content(text: str, covered: list[tuple[int, int]] = ()) -> tuple[int, list[Finding]]:
    """Returns (content risk score 0-100, findings for each risky sentence).

    `covered` = character spans already reported as personal info. A sentence that is
    explained by those findings (e.g. "Born 12/05/2004.") is not counted a second time.
    """
    items = [(s, o) for s, o in _sentences_with_offsets(text) if not _explained_by_pii(s, o, list(covered))]
    if not items:
        return 0, []
    sentences = [s for s, _ in items]

    probabilities = get_model().predict_proba(sentences)[:, 1]
    why, fix = describe("Risky post")
    findings = []
    for sentence, p in zip(sentences, probabilities):
        if p >= RISKY_THRESHOLD:
            findings.append(Finding(
                category="content",
                type=f"Risky post ({p:.0%} confidence)",
                value=redact(sentence)[:160],
                severity="high" if p >= 0.8 else "medium",
                source="ML model",
                confidence=round(float(p), 2),
                explanation=why,
                fix=fix,
            ))

    # The score comes only from posts that were actually flagged (see risk_scorer)
    return content_breakdown(findings)[0], findings
