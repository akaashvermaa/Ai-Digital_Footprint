# AI Digital Footprint Risk Analyzer

A web app that measures how exposed a person is online. The user enters their
**username**, **email** and/or **bio/post text**, and the app:

1. **Detects personal information** in the text using NLP (regex + context rules + spaCy NER)
2. **Flags risky posts** using a machine-learning classifier we trained (TF-IDF + Logistic Regression)
3. **Scans 45 websites** to see where the username exists (OSINT, like the tool *Sherlock*)
4. **Checks data breaches** for the email (free XposedOrNot API)
5. Combines everything into a **0-100 risk score** (Low / Medium / High) where **every point is traceable to a finding**
6. Explains each finding (*why it is risky*, *what to do*, *how confident we are*), gives **prioritised advice** and a downloadable **PDF report**

---

## Quick start (Windows)

Install **Python 3.10+** (tick "Add Python to PATH") and **Node.js LTS**, then **double-click `start.bat`**.

- The first run sets everything up (a few minutes, needs internet), then every run after that starts in seconds.
- It opens two black windows (backend and frontend) and your browser at http://localhost:5173.
- To stop the app, close the two black windows or double-click `stop.bat`.

If something fails, the launcher says what to fix. The manual steps below do the same thing by hand.

## How to run manually

You need **Python 3.10+** and **Node.js 18+**. Use two terminals.

**Terminal 1: backend (Python)**
```powershell
cd backend
python -m venv venv                          # first time only
.\venv\Scripts\pip install -r requirements.txt   # first time only
.\venv\Scripts\python -m spacy download en_core_web_sm   # first time only
.\venv\Scripts\python train_model.py         # first time only: trains the ML model
.\venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2: frontend (React)**
```powershell
cd frontend
npm install        # first time only
npm run dev
```

Open **http://localhost:5173** and click **"Fill example"** to try it.
API documentation is generated automatically at http://localhost:8000/docs.

**Run the tests (53):** `cd backend` then `.\venv\Scripts\python -m pytest`
**Re-measure accuracy:** `cd backend` then `.\venv\Scripts\python evaluate.py` (writes `backend/evaluation/RESULTS.md`)

---

## Architecture

```
 React frontend (Vite, port 5173)
   InputForm -> POST /api/analyze -> Dashboard (gauge, chart, findings, advice)
                POST /api/report  -> PDF download
        |
        v
 FastAPI backend (port 8000)        security.py: input cleaning, rate limit, safe headers, friendly errors
   /api/analyze runs these in parallel (asyncio); each one is isolated, so a failure
   becomes "could not check" instead of breaking the whole result:
     |- pii_detector.py      regex + context rules + spaCy NER  -> personal info findings
     |- text_risk_model.py   TF-IDF + LogisticRegression         -> risky post findings
     |- username_checker.py  async HTTP to 45 sites              -> accounts found / unknown
     '- breach_checker.py    XposedOrNot API                     -> breaches
   risk_scorer.py      weighted score 0-100 with a list of contributions
   summary.py          plain-language summary + limitations
   recommendations.py  advice sorted into urgent / important / good practice
   explanations.py     "why is this risky" + "what to do" for each finding type
   report_pdf.py       ReportLab PDF
```

### Folder structure
| Path | What it does |
|---|---|
| `backend/app/main.py` | API routes, input validation, runs the checks in parallel and isolates failures |
| `backend/app/security.py` | Input cleaning, rate limit, security headers, error handlers, CORS |
| `backend/app/schemas.py` | Data models with size limits (Pydantic) |
| `backend/app/services/` | `pii_detector`, `text_risk_model`, `username_checker`, `breach_checker`, `risk_scorer`, `recommendations`, `summary`, `explanations`, `report_pdf` |
| `backend/app/data/` | `sites.json` (the 45 sites), `training_posts.csv` (236 labelled posts) |
| `backend/evaluate.py` + `backend/evaluation/` | Test sets, scenarios and the generated `RESULTS.md` |
| `backend/tests/` | 53 automated tests |
| `frontend/src/` | `App.jsx` and `components/` (form, gauge, chart, findings, accounts, breaches, advice) |

---

## How the AI works

### 1. Personal information detection (NLP)
- **Regex** catches data with a fixed format: phone numbers, emails, Aadhaar, PAN, vehicle numbers, URLs,
  college names (IIT/NIT/"... University").
- **Context rules** decide when a number or date really is personal:
  a 6-digit number is a PIN code only near "pincode" or an address; a date is a date of birth only in a
  sentence with "born/birthday/DOB" and not in the future; "2 weeks" is never a birthday.
- **spaCy NER** (`en_core_web_sm`) finds person names, places and organisations. The small model is noisy,
  so its output is filtered: lowercase words are not places, app names (WhatsApp, Python...) are never
  organisations, a lone first name needs a cue like "my name is", and an organisation needs a cue like
  "at / joined / working at". A gazetteer of ~90 Indian cities and states is added before the NER.
- **Duplicates are merged:** `9876543210`, `98765 43210` and `+91 9876543210` become one finding with
  `occurrences = 3`, so one exposure never inflates the score.
- Every finding carries a **confidence** (regex ids ~0.95, context rules 0.7-0.85, NER guesses 0.55-0.65).
- Sensitive values (phone, Aadhaar, PAN, email) are **masked** in results, e.g. `98****3210`.

### 2. Risky-post classifier (Machine Learning)
- **Dataset:** 236 hand-labelled posts (115 risky / 121 safe). Risky ones reveal travel plans/empty house,
  routines, documents, passwords/OTP, security-question answers, addresses, valuables.
- **Features:** TF-IDF on character n-grams (2-5 letters), which handle typos and word forms.
- **Model:** Logistic Regression, which outputs a probability that we show as confidence.
- Each sentence is classified separately; sentences at 60% or above are reported.
- **No double counting:** a sentence already explained by a personal-info finding (e.g. "Born 12/05/2004.")
  is not also counted as a risky post.

### 3. Risk score (transparent and testable)
Every category score is the **sum of contributions**, and every contribution comes from a real finding.

| Category | Weight | How its 0-100 score is built |
|---|---|---|
| Personal info exposure | 40% | Per finding **type**: first finding earns full points (high 25 / medium 12 / low 5), each extra one of the same type earns 30% of that, and a type can never earn more than 2x its base (eight cities = 24 points, not 96) |
| Data breaches | 30% | 1 breach = 40, 2 = 55, 3 = 65, then +2 each up to 85; +15 if passwords leaked; +10 if phone/address/DOB/ID leaked |
| Risky content | 15% | Confidence of the riskiest post x 100, +5 for each further risky post; 0 if nothing was flagged |
| Account spread | 15% | 8 points per site where the username exists |

Only the checks that actually ran count, and the weights are re-normalised. A check that **failed** is shown as
"could not check" and left out of the score (it is *unknown*, not zero).
**Levels:** 0-30 Low, 31-60 Medium, 61-100 High.

**Worked example** (the "Fill example" input): personal info 79 (phone 25 + date of birth 25 + school 12 +
place 12 + name 5), breaches 100 (85 + 15 passwords + 10 sensitive data), content 91 (86 + 5),
accounts 100 (15 sites x 8, capped) -> `0.40x79 + 0.30x100 + 0.15x91 + 0.15x100 = 90` -> **High**.

---

## Evaluation (measured, reproducible: `python evaluate.py`)

> All datasets were written by the project developers, which biases them towards our own style. Results are
> **preliminary** on small educational datasets, not proof of reliability on the wider internet.

**PII detector** (a finding is correct if its *type* was expected for that text)

| Test set | Texts | Precision | Recall | F1 | Note |
|---|---|---|---|---|---|
| Development set, before fixes | 48 | 0.75 | 0.98 | 0.85 | baseline: 14 false alarms (random words labelled organisations, "100000 points" as PIN code, ...) |
| Development set, after fixes | 48 | 1.00 | 1.00 | 1.00 | rules were tuned on these, so this is **not** evidence |
| Unseen set, first run | 43 | 0.94 | 0.97 | 0.96 | two general weaknesses found and fixed; set is now also "used" |
| **Final set (run once, never tuned on)** | 36 | **0.94** | **0.94** | **0.94** | the honest estimate; weakest type: person names |

**Risky-post model**

| Measurement | Result |
|---|---|
| 5-fold cross-validation on the 236 training posts (re-fitted inside each fold, no leakage) | precision 0.95, recall 0.94, **F1 0.94** (was 0.92 on the first 202 posts) |
| Held-out set of 70 posts never used for training | precision 0.89, recall 0.97, **F1 0.93**, accuracy 92.9% (4 false alarms, 1 miss) |

The held-out errors are *awareness* posts that talk about security ("tips for keeping your home safe while
travelling", "the bank called to warn about fraud") which the model confuses with real leaks. We looked at
these errors but deliberately did **not** train towards them; the training additions only targeted categories
found by cross-validation on the training data.

**Scoring scenarios:** 7 of 7 realistic personas land in the level decided in advance
(clean user Low, travel-only post Medium, single mild breach Medium, heavy breach with passwords High, ...).
Table in `backend/evaluation/RESULTS.md`; automated in `tests/test_scenarios.py`.

---

## Privacy and security
- **Nothing is stored:** no database, and inputs are never logged (error handlers log only the exception type).
- **Consent:** the user must confirm they are checking their own information (or have permission), and the
  form says exactly where data goes: the username is sent to 45 public websites, the email to XposedOrNot,
  the text is processed only on our server. Users are told never to paste passwords.
- **Input validation:** length limits (username 2-40 with an allowed-character check, email format, text
  10,000 characters), control and invisible/bidi characters stripped, readable error messages that never echo the input.
- **Abuse protection:** rate limit of 10 analyses per minute per IP (each one contacts 45 sites); the PDF
  endpoint accepts only size-limited payloads.
- **Safe responses:** `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`,
  `X-Frame-Options: DENY`; CORS allows only the configured frontend.
- **Safe rendering:** React escapes all output (no `dangerouslySetInnerHTML`); PDF text is escaped.
- **Secrets:** configuration comes from environment variables (`backend/.env.example`); no keys are in the code.
- **Public data only:** no logins, no scraping behind logins, nothing is hacked.

### Deploying
Serve the app behind **HTTPS** (a reverse proxy such as Nginx or Caddy), set `ALLOWED_ORIGINS` to your real
frontend URL, and put the proxy in front of uvicorn. The rate limiter is in-memory and uses the direct client
IP, so behind a proxy configure the proxy to rate-limit as well.

## Limitations
- The datasets are small and written by us; accuracy on real-world text will be lower.
- Person-name detection (spaCy small model) is the weakest part; names are marked low severity for this reason.
- The risky-post model cannot tell a warning about leaks from an actual leak.
- A username match only means an account with that name exists; it may belong to someone else.
- Instagram, X, Facebook and LinkedIn block automated checks, so they are not scanned; some of the 45 sites
  can also block requests, and those are reported as "could not be checked" instead of "not found".
- English and Hinglish text only; no image analysis.

## Future scope
Image analysis (detect documents and number plates in photos with OCR), a larger labelled dataset,
Hindi/Hinglish models, a browser extension that warns before posting, and scan history with user accounts.

## Tech stack
Python, FastAPI, spaCy, scikit-learn, pandas, httpx, ReportLab, pytest ·
React, Vite
