# Evaluation results

Generated 19 Oct 2026 by `python evaluate.py` (seed 42).

## 1a. PII detector - development set (rules were tuned on these)

48 labelled texts. A finding counts as correct when its *type* was expected for that text.

**Overall: precision 1.00, recall 1.00, F1 1.00** (TP 42, FP 0, FN 0); texts with exactly the right set of types: 48/48

| Type | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| Aadhaar number | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Date of birth | 5 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Email address | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Home address hint | 4 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Link / URL | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Location | 10 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Organisation (school/work) | 4 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| PAN number | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| PIN code | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Person name | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Phone number | 6 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Vehicle number | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |

**Missed (false negatives):**

- none

**False alarms (false positives):**

- none

## 1b. PII detector - unseen set (written without looking at the detector)

43 labelled texts. A finding counts as correct when its *type* was expected for that text.

**Overall: precision 1.00, recall 1.00, F1 1.00** (TP 33, FP 0, FN 0); texts with exactly the right set of types: 43/43

| Type | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| Aadhaar number | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Date of birth | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Email address | 3 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Home address hint | 3 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Link / URL | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Location | 8 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Organisation (school/work) | 4 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| PAN number | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| PIN code | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Person name | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Phone number | 5 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Vehicle number | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |

**Missed (false negatives):**

- none

**False alarms (false positives):**

- none

## 1c. PII detector - final test set (run once, never tuned on)

36 labelled texts. A finding counts as correct when its *type* was expected for that text.

**Overall: precision 0.94, recall 0.94, F1 0.94** (TP 34, FP 2, FN 2); texts with exactly the right set of types: 32/36

| Type | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| Aadhaar number | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Date of birth | 3 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Email address | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Home address hint | 4 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Link / URL | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Location | 11 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Organisation (school/work) | 3 | 0 | 1 | 1.00 | 0.75 | 0.86 |
| PAN number | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| PIN code | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Person name | 1 | 2 | 1 | 0.33 | 0.50 | 0.40 |
| Phone number | 5 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Vehicle number | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |

**Missed (false negatives):**

- `Working at TCS in Chennai since 2021` -> Organisation (school/work)
- `Thanks Ravi Kumar for helping me with the project` -> Person name

**False alarms (false positives):**

- `Send it to flat no 12, Palm Residency, pincode 400053` -> Person name
- `Hello everyone, my name is Aditya and I am new here` -> Person name

## 2. Risky-post ML model

Training set: 236 posts (115 risky / 121 safe), duplicates: 0. Held-out set: 70 posts, overlap with training: 0.

### 5-fold cross-validation (training CSV)

Precision 0.95, recall 0.94, F1 0.94. Confusion matrix: TN 115, FP 6, FN 7, TP 108.

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

## 3. Risk score scenarios

Expected levels were decided from the design of the formula before running. Network checks are replaced by fixed data so the table is reproducible.

| Scenario | Expected | Score | Level | Match |
|---|---|---|---|---|
| Clean user: harmless post only | Low | 0 | Low | yes |
| Careful user: 2 public accounts | Low | 16 | Low | yes |
| Travel-only post (house empty) | Medium | 32 | Medium | yes |
| Email in a single, mild breach | Medium | 40 | Medium | yes |
| Username on 4 sites only | Medium | 32 | Medium | yes |
| Heavy breach with passwords leaked | High | 98 | High | yes |
| Over-sharing student: everything | High | 85 | High | yes |

7/7 scenarios in the expected level.
