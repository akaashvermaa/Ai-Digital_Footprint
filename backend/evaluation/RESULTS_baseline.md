# Evaluation results

Generated 19 Oct 2026 by `python evaluate.py` (seed 42).

## 1. PII detector

48 labelled texts. A finding counts as correct when its *type* was expected for that text.

**Overall: precision 0.75, recall 0.98, F1 0.85** (TP 42, FP 14, FN 1); texts with exactly the right set of types: 33/48

| Type | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| Aadhaar number | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Date (possible DOB) | 0 | 2 | 0 | 0.00 | 0.00 | 0.00 |
| Date of birth | 5 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Email address | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Home address hint | 4 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Link / URL | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Location | 10 | 0 | 1 | 1.00 | 0.91 | 0.95 |
| Organisation (school/work) | 4 | 7 | 0 | 0.36 | 1.00 | 0.53 |
| PAN number | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| PIN code | 2 | 2 | 0 | 0.50 | 1.00 | 0.67 |
| Person name | 2 | 2 | 0 | 0.50 | 1.00 | 0.67 |
| Phone number | 6 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Place / building | 0 | 1 | 0 | 0.00 | 0.00 | 0.00 |
| Vehicle number | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |

**Missed (false negatives):**

- `Studying at IIT Kanpur these days` -> Location

**False alarms (false positives):**

- `Call 9876543210. WhatsApp: 98765 43210 or +91 9876543210` -> Organisation (school/work)
- `My Aadhaar is 2345 6789 0123` -> Organisation (school/work)
- `PAN card number ABCDE1234F is attached` -> Organisation (school/work)
- `DOB: 21.11.2003` -> Organisation (school/work)
- `Exam is on 12/05/2026, wish me luck` -> Date (possible DOB)
- `Team meeting on 3 March at the office` -> Date (possible DOB)
- `Bike UP32 AB 4321 is my lucky number plate` -> Organisation (school/work)
- `I live in Lajpat Nagar, New Delhi 110024` -> Person name
- `I scored 100000 points in the game and have 250000 followers` -> PIN code
- `The video got 150000 views in two days` -> PIN code
- `Message me on WhatsApp or Instagram anytime` -> Organisation (school/work)
- `Follow me on Snapchat and YouTube` -> Person name
- `Learning Python and React this semester` -> Organisation (school/work)
- `I live near the metro station` -> Place / building

## 2. Risky-post ML model

Training set: 202 posts (100 risky / 102 safe), duplicates: 0. Held-out set: 70 posts, overlap with training: 0.

### 5-fold cross-validation (training CSV)

Precision 0.90, recall 0.93, F1 0.92. Confusion matrix: TN 92, FP 10, FN 7, TP 93.

### Held-out set (never used for training or tuning)

**Precision 0.89, recall 0.97, F1 0.93**, accuracy 92.86%. Confusion matrix: TN 31, FP 4, FN 1, TP 34.

```
precision    recall  f1-score   support

        safe       0.97      0.89      0.93        35
       risky       0.89      0.97      0.93        35

    accuracy                           0.93        70
   macro avg       0.93      0.93      0.93        70
weighted avg       0.93      0.93      0.93        70
```

**Held-out errors:**

- FN (missed risky): Told the courier my OTP, fingers crossed the refund comes
- FP (false alarm): My password manager finally synced across all my devices
- FP (false alarm): Tips for keeping your home safe while travelling: use timers on lights
- FP (false alarm): Our company is hiring interns, send your resume through the portal
- FP (false alarm): The bank called to warn about fraud, glad they care

> Preliminary results on a small educational dataset. They show the approach works on posts written in the same style; they are **not** proof of reliability on the wider internet.
