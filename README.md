# AI Digital Footprint Risk Analyzer

A web application that shows how exposed a person is online and what to fix first.

The user enters a **username**, an **email address** and/or some **bio or post text**. The app then:

1. Finds personal information in the text (phone, ID numbers, school, places, names) using NLP.
2. Flags risky posts (travel plans, routines, documents, secrets) using a machine-learning model trained for this project.
3. Checks 62 public websites to see where the username exists.
4. Checks whether the email appears in known data breaches.
5. Combines everything into a single **0 to 100 risk score** (Low, Medium or High) in which every point is traceable to a finding.
6. Explains each finding, gives advice sorted by priority, and produces a downloadable PDF report.

This is a minor project. It is a learning project, not a security product, and its limits are listed honestly below.

---

## Contents

- [Quick start (Windows)](#quick-start-windows)
- [Run it manually](#run-it-manually)
- [Using the app](#using-the-app)
- [How it works](#how-it-works)
- [Design decisions](#design-decisions)
- [The risk score](#the-risk-score)
- [Accuracy](#accuracy)
- [Privacy and security](#privacy-and-security)
- [Configuration](#configuration)
- [Maintenance](#maintenance)
- [Limitations](#limitations)
- [Future scope](#future-scope)
- [Tech stack](#tech-stack)
- [Team](#team)

---

## Quick start (Windows)

1. Install **Python 3.10 or newer** (tick "Add Python to PATH" in the installer) and **Node.js LTS**.
2. Double-click **`start.bat`**.

The first run sets everything up and needs internet (a few minutes). Every run after that starts in seconds.
It opens two black windows (backend and frontend) and your browser at http://127.0.0.1:5173.

To stop the app, close the two black windows or double-click `stop.bat`.

If something fails, the launcher prints what to fix.

## Run it manually

Requirements: Python 3.10+ and Node.js 18+. Use two terminals.

**Terminal 1: backend**

```powershell
cd backend
python -m venv venv                                      # first time only
.\venv\Scripts\pip install -r requirements.txt           # first time only
.\venv\Scripts\python -m spacy download en_core_web_sm   # first time only
.\venv\Scripts\python train_model.py                     # first time only: trains the ML model
.\venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2: frontend**

```powershell
cd frontend
npm install        # first time only
npm run dev
```

Open http://127.0.0.1:5173. Interactive API documentation is at http://127.0.0.1:8000/docs.

The address `127.0.0.1` is used on purpose instead of `localhost`. On Windows, `localhost` can resolve to
IPv6 while the backend listens on IPv4, which makes the app look unreachable.

## Using the app

1. Click **Fill example** to load a sample, or type your own username, email and text.
2. Tick the consent box (you confirm you are checking your own information or have permission).
3. Press **Analyse**.
4. Read the score, the list of findings (what was found, why it is risky, what to do), the accounts found,
   the breaches, and the prioritised advice.
5. Download the PDF report if you want to keep it.

The example input produces a score of 90 (High).

---

## How it works

```
React frontend (port 5173)
   InputForm  --POST /api/analyze-->  results page
              --POST /api/report--->  PDF download
        |
        v
FastAPI backend (port 8000)
   security.py   input cleaning, rate limit, safe headers, friendly errors
   /api/analyze runs four checks in parallel. Each is isolated: if one fails it is
   shown as "could not check" and the rest still return.
     |- pii_detector.py      regex + context rules + spaCy NER      -> personal information
     |- text_risk_model.py   TF-IDF + Logistic Regression           -> risky posts
     |- username_checker.py  async HTTP requests to 62 sites        -> accounts found
     '- breach_checker.py    XposedOrNot API                        -> data breaches
   risk_scorer.py      combines the results into the 0-100 score and its contributions
   summary.py          plain-language summary and limitations
   recommendations.py  advice grouped as urgent, important, good practice
   explanations.py     "why is this risky" and "what to do" for each finding type
   report_pdf.py       PDF report (ReportLab)
```

### Folder structure

| Path | Purpose |
|---|---|
| `start.bat`, `stop.bat` | One-click launcher and stopper for Windows |
| `backend/app/main.py` | API routes, validation, runs the checks in parallel, isolates failures |
| `backend/app/security.py` | Input cleaning, rate limit, security headers, error handlers, CORS |
| `backend/app/schemas.py` | Request and response models with size limits (Pydantic) |
| `backend/app/services/` | The four checks, the scorer, the summary, the advice and the PDF |
| `backend/app/data/` | `sites.json` (the 62 websites) and `training_posts.csv` (236 labelled posts) |
| `backend/train_model.py` | Trains and saves the risky-post model |
| `backend/evaluate.py` | Measures accuracy and writes `backend/evaluation/RESULTS.md` |
| `backend/check_sites.py` | Re-checks that every website in `sites.json` still works |
| `backend/evaluation/` | Test sets and scenarios used for measuring |
| `backend/tests/` | 53 automated tests |
| `frontend/src/` | `App.jsx`, `api.js` and the components (form, score, breakdown, findings, accounts, breaches, advice, limitations) |

### 1. Personal information detection (NLP)

- **Regex** catches data with a fixed shape: phone numbers, emails, Aadhaar, PAN, vehicle numbers, URLs,
  and college names (IIT, NIT, "... University").
- **Context rules** decide when a number or date is really personal. A 6-digit number is a PIN code only
  near words like "pincode" or an address. A date is a date of birth only in a sentence with "born",
  "birthday" or "DOB", and not in the future. A duration such as "2 weeks" is never a birthday.
- **spaCy NER** (`en_core_web_sm`) finds person names, places and organisations. The small model is noisy,
  so its output is filtered: lowercase words are not places, app names (WhatsApp, Python) are never
  organisations, a lone first name needs a cue such as "my name is", and an organisation needs a cue such as
  "at", "joined" or "working at". About 90 Indian cities and states are added as a place list.
- **Duplicates are merged.** `9876543210`, `98765 43210` and `+91 9876543210` become one finding with
  `occurrences = 3`, so one exposure cannot inflate the score.
- Every finding has a **confidence** (regex ids about 0.95, context rules 0.7 to 0.85, NER guesses 0.55 to 0.65).
- Sensitive values (phone, Aadhaar, PAN, email) are **masked** in results, for example `98****3210`.

### 2. Risky-post classifier (machine learning)

- **Data:** 236 hand-written, hand-labelled posts (115 risky, 121 safe). Risky posts reveal travel plans or an
  empty house, routines, documents, passwords or OTPs, security-question answers, addresses and valuables.
- **Features:** TF-IDF on character n-grams (2 to 5 letters). This copes with typos and word forms.
- **Model:** Logistic Regression, which outputs a probability that is shown as the confidence.
- Each sentence is classified separately and sentences at 60% or above are reported.
- **No double counting:** a sentence already explained by a personal-information finding
  (for example "Born 12/05/2004.") is not also counted as a risky post.

### 3. Username scan

The username is requested on 62 public websites at the same time (about 5 seconds in total). For each site the
answer is one of: found, not found, or could not check (blocked, rate-limited, timed out). A site that cannot be
checked is never counted as "not found". A match only means an account with that name exists; it may belong to
someone else.

### 4. Breach check

The email is sent to the free XposedOrNot service. The result lists the breaches and whether passwords or other
sensitive data were exposed. If the service is down, the result says so instead of guessing.

---

## Design decisions

These are the main choices and the simple reason behind each.

| Decision | Reason |
|---|---|
| Rules plus a small model, not a large AI model | Every result can be explained, it runs offline and it costs nothing to run |
| Logistic Regression for risky posts | Simple, fast, works with a small dataset and gives a probability |
| Fixed weights for the score | A teacher or user can verify the arithmetic by hand |
| Diminishing returns per finding type | Eight cities in one post must not score like eight different secrets |
| A failed check is "unknown", not zero | Otherwise a network error would make someone look safer than they are |
| Nothing is stored | The tool handles personal data, so the safest design is to keep none |
| Only public data, no logins | The tool must not do anything a normal visitor cannot do |
| Skip sites that block bots (Instagram, X, Facebook, LinkedIn) | Their answers would be unreliable, so they are left out |
| Separate test sets | Rules were tuned on one set, so honest numbers come from texts the rules never saw |
| `127.0.0.1` instead of `localhost` | Avoids an IPv4 and IPv6 mismatch on Windows |

---

## The risk score

Every category score is the **sum of contributions**, and every contribution comes from a real finding.
The contributions are listed in the result and in the PDF.

| Category | Weight | How its 0 to 100 score is built |
|---|---|---|
| Personal information | 40% | Per finding type: the first finding earns full points (high 25, medium 12, low 5), each extra one of the same type earns 30% of that, and a type can never earn more than twice its base. Eight cities give 24 points, not 96 |
| Data breaches | 30% | 1 breach = 40, 2 = 55, 3 = 65, then +2 each up to 85. Add 15 if passwords leaked and 10 if phone, address, date of birth or ID leaked |
| Risky content | 15% | Confidence of the riskiest post x 100, plus 5 for each further risky post. 0 if nothing was flagged |
| Account spread | 15% | 8 points per site where the username exists, capped at 100 |

Only checks that actually ran count, and the weights are re-normalised over them. A check that failed is shown
as "could not check" and left out.

**Levels:** 0 to 30 Low, 31 to 60 Medium, 61 to 100 High.

**Worked example (the "Fill example" input):**

| Check | Score | Weight | Points |
|---|---|---|---|
| Personal information | 79 | 40% | 31.6 |
| Data breaches | 100 | 30% | 30.0 |
| Risky content | 91 | 15% | 13.7 |
| Accounts | 100 | 15% | 15.0 |
| **Total** | | | **90 (High)** |

---

## Accuracy

Everything here is measured and reproducible with `python evaluate.py`.

> All datasets were written by the project developers, which biases them towards our own writing style.
> The results are preliminary results on small educational datasets. They are not proof of reliability on the wider internet.

**Personal information detector** (a finding counts as correct if its type was expected for that text)

| Test set | Texts | Precision | Recall | F1 | Note |
|---|---|---|---|---|---|
| Development set, before fixes | 48 | 0.75 | 0.98 | 0.85 | Baseline with 14 false alarms |
| Development set, after fixes | 48 | 1.00 | 1.00 | 1.00 | Rules were tuned on these, so this is not evidence |
| Unseen set, first run | 43 | 0.94 | 0.97 | 0.96 | Two general weaknesses found and fixed; the set is now also "used" |
| **Final set (run once, never tuned on)** | 36 | **0.94** | **0.94** | **0.94** | The honest estimate; weakest type is person names |

**Risky-post model**

| Measurement | Result |
|---|---|
| 5-fold cross-validation on the 236 training posts (re-fitted inside each fold) | precision 0.95, recall 0.94, F1 0.94 |
| Held-out set of 70 posts never used for training | precision 0.89, recall 0.97, F1 0.93, accuracy 92.9% |

The held-out errors are awareness posts that talk about security ("tips for keeping your home safe while
travelling"), which the model confuses with real leaks. We looked at these errors but deliberately did not train
towards them.

**Scoring scenarios:** 7 of 7 realistic personas land in the level decided in advance (clean user Low,
travel-only post Medium, single mild breach Medium, heavy breach with passwords High, and so on). The table is in
`backend/evaluation/RESULTS.md` and the check is automated in `backend/tests/test_scenarios.py`.

---

## Privacy and security

- **Nothing is stored.** There is no database, and inputs are never logged (error handlers log only the exception type).
- **Consent.** The user must confirm they are checking their own information or have permission. The form says
  exactly where data goes: the username to 62 public websites, the email to XposedOrNot, the text only to our
  own server. Users are told never to paste passwords.
- **Input validation.** Length limits (username 2 to 40 characters with an allowed-character check, email format,
  text up to 10,000 characters). Control characters and invisible or bidirectional characters are removed.
  Error messages are readable and never repeat the input.
- **Abuse protection.** A limit of 10 analyses and 20 PDF downloads per minute per IP address, because each
  analysis contacts 62 third-party sites. The PDF endpoint accepts only size-limited requests.
- **Safe responses.** `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`,
  `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`. CORS allows only the configured frontend.
- **Safe rendering.** React escapes all output (no `dangerouslySetInnerHTML`) and PDF text is escaped.
- **No secrets in code.** Settings come from environment variables.
- **Public data only.** No logins, no scraping behind logins, nothing is hacked.

## Configuration

The backend reads two settings from **environment variables**. It does not read the `.env.example` file by
itself; that file is a template listing the names.

| Variable | Default | Meaning |
|---|---|---|
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Frontend addresses allowed to call the API (comma separated) |
| `RATE_LIMIT_PER_MIN` | `10` | Analyses allowed per minute per IP address (PDF downloads get twice this) |

PowerShell example:

```powershell
$env:RATE_LIMIT_PER_MIN = "5"
.\venv\Scripts\python -m uvicorn app.main:app --port 8000
```

To deploy, serve the app behind HTTPS (a reverse proxy such as Nginx or Caddy), set `ALLOWED_ORIGINS` to the
real frontend address and put the proxy in front of uvicorn. The rate limiter is in memory and uses the direct
client address, so behind a proxy the proxy should rate-limit as well.

## Maintenance

All commands are run from the `backend` folder.

| Task | Command |
|---|---|
| Run the tests (53) | `.\venv\Scripts\python -m pytest` |
| Re-measure accuracy | `.\venv\Scripts\python evaluate.py` (writes `evaluation/RESULTS.md`) |
| Retrain the risky-post model | `.\venv\Scripts\python train_model.py` |
| Check that all 62 websites still work | `.\venv\Scripts\python check_sites.py` |

Websites change: they start blocking automated requests, move URLs or answer "found" for everything.
`check_sites.py` tests every site with usernames that very likely exist (at least one must be found) and with
made-up usernames (none may be found). Run it before a demo. If a site fails twice in a row, remove it from
`backend/app/data/sites.json`. Each entry looks like this:

```json
{"name": "GitHub", "category": "Developer", "url": "https://github.com/{}", "probe": "https://api.github.com/users/{}", "check": "status"}
```

The `check` field is `status` (HTTP 200 means found), `absent_text` (found unless the page contains a "not found"
marker) or `present_text` (found only if the page contains a marker). The optional `probe` URL is requested
instead of the profile page, which is useful when a public API answers more reliably than the website.

## Limitations

- The datasets are small and written by us, so accuracy on real-world text will be lower.
- Person-name detection (the small spaCy model) is the weakest part, so names are marked low severity.
- The risky-post model cannot tell a warning about leaks from an actual leak.
- A username match only means an account with that name exists; it may belong to someone else.
- Instagram, X, Facebook and LinkedIn block automated checks, so they are not scanned. Some of the 62 sites can
  also block requests; those are reported as "could not check" rather than "not found".
- English and Hinglish text only, and no image analysis.

## Future scope

- Image analysis: detect documents and number plates in photos with OCR.
- A larger labelled dataset and Hindi or Hinglish models.
- A browser extension that warns before posting.
- Scan history with user accounts.

## Tech stack

- **Backend:** Python, FastAPI, spaCy, scikit-learn, pandas, httpx, ReportLab, pytest
- **Frontend:** React, Vite

## Team

| Name | Roll number |
|---|---|
| Akash Verma | 108002240006 |
| Amit Kumar Sharma | 108002240012 |

Under the guidance of Dr. Vedatrayee Chatterjee (Head of the IT Department) and Mr. Biplab Kumar Mandal (Coordinator).
