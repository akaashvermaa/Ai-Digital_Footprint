"""Detects personal information (PII) in free text.

Layers (each reports a confidence, so the UI can say how sure we are):
1. Regex   - data with a fixed format (phone, email, Aadhaar, PAN, vehicle, college, ...).
2. Context - a number or date only counts when the words around it say so
             (a 6-digit number is a PIN code only near "pincode" or an address).
3. spaCy   - Named Entity Recognition for names, places and organisations, filtered
             with rules because the small model produces noisy guesses.
The same value written in different ways (98765 43210 / +91 9876543210) is merged
into a single finding with an occurrence count.
"""
import re
from datetime import date

import spacy

from app.schemas import Finding
from app.services.explanations import describe

INDIAN_PLACES = """
delhi;new delhi;mumbai;bombay;kolkata;calcutta;chennai;madras;bengaluru;bangalore;
hyderabad;pune;ahmedabad;surat;jaipur;lucknow;kanpur;nagpur;indore;bhopal;patna;
vadodara;ghaziabad;ludhiana;agra;nashik;faridabad;meerut;rajkot;varanasi;srinagar;
amritsar;allahabad;prayagraj;ranchi;coimbatore;jabalpur;gwalior;vijayawada;jodhpur;
madurai;raipur;kota;chandigarh;guwahati;noida;greater noida;gurgaon;gurugram;
dehradun;mysore;mysuru;thiruvananthapuram;kochi;bhubaneswar;visakhapatnam;shimla;
goa;panaji;manali;rishikesh;udaipur;mathura;aligarh;bareilly;moradabad;
uttar pradesh;madhya pradesh;maharashtra;rajasthan;gujarat;punjab;haryana;bihar;
west bengal;karnataka;kerala;tamil nadu;telangana;andhra pradesh;odisha;assam;
jharkhand;chhattisgarh;uttarakhand;himachal pradesh;jammu;kashmir;sikkim
"""
INDIAN_PLACES = [p.strip() for p in INDIAN_PLACES.replace("\n", "").split(";") if p.strip()]
PLACE_SET = set(INDIAN_PLACES)
PLACE_RE = re.compile(r"\b(?:" + "|".join(re.escape(p) for p in sorted(INDIAN_PLACES, key=len, reverse=True)) + r")\b", re.I)

_nlp = None


def get_nlp():
    """Load the spaCy model once and reuse it (loading takes ~1 second)."""
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
        # The small English model misses many Indian place names, so a rule-based
        # "gazetteer" runs before the statistical NER.
        ruler = _nlp.add_pipe("entity_ruler", before="ner")
        ruler.add_patterns([
            {"label": "GPE", "pattern": [{"LOWER": w} for w in place.split()]}
            for place in INDIAN_PLACES
        ])
    return _nlp


# Words spaCy often mislabels as organisations/people/places but which are apps, tech or ID names
NOT_ENTITIES = {
    "whatsapp", "instagram", "insta", "snapchat", "youtube", "google", "facebook", "twitter", "telegram",
    "linkedin", "github", "python", "react", "java", "javascript", "aadhaar", "aadhar", "pan", "dob",
    "netflix", "amazon", "flipkart", "paytm", "gpay", "phonepe", "upi", "otp", "atm", "wifi", "iphone",
    "android", "windows", "chatgpt", "reddit", "tiktok", "discord", "zoom", "excel", "sql", "css", "html",
    "dm", "pin", "id", "ifsc", "gmail", "yahoo", "outlook", "spotify", "marvel", "batman",
}
COUNTRIES = {"india", "usa", "uk", "america", "england", "china", "japan", "australia", "canada", "germany", "france"}

# (type, pattern, severity, confidence). Order matters: earlier patterns claim text first.
ID_RULES = [
    ("Email address", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "medium", 0.95),
    ("Aadhaar number", re.compile(r"\b\d{4}[\s-]\d{4}[\s-]\d{4}\b"), "high", 0.85),
    ("PAN number", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), "high", 0.95),
    ("Phone number", re.compile(r"(?<!\d)(?:\+91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"), "high", 0.95),
    ("Phone number", re.compile(r"\+\d{1,3}[\s-]?\d{3,4}[\s-]?\d{3,4}[\s-]?\d{3,4}"), "high", 0.9),
    ("Vehicle number", re.compile(r"\b[A-Z]{2}[\s-]?\d{1,2}[A-Z]?[\s-]?[A-Z]{1,3}[\s-]?\d{4}\b"), "medium", 0.8),
    ("Organisation (school/work)", re.compile(
        r"\b(?:IIT|IIIT|NIT|AIIMS|BITS|IIM)\s+[A-Z][a-z]+\b|"
        r"\b(?:[A-Z][\w.&]*\s+){1,4}(?:University|College|School|Institute|Academy|Vidyalaya)\b"), "medium", 0.8),
    ("Location", re.compile(
        r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)?\s(?:Nagar|Vihar|Colony|Enclave|Puram|Bagh|Marg|Kunj|Extension|"
        r"Place|Market|Mall|Airport|Bazaar|Chowk)\b"), "medium", 0.75),
    ("Link / URL", re.compile(r"\bhttps?://\S+|\bwww\.\S+"), "low", 0.95),
]
REGEX_RULES = ID_RULES   # kept for redact()

MONTHS = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
DATE_RULES = [
    re.compile(r"\b\d{1,2}[/.-]\d{1,2}[/.-](?:19|20)?\d{2}\b"),
    re.compile(
        rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:of\s+)?{MONTHS}(?:,?\s+(?:19|20)\d{{2}})?\b|"
        rf"\b{MONTHS}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+(?:19|20)\d{{2}})?\b", re.I),
]
PIN_RE = re.compile(r"(?<!\d)[1-9]\d{5}(?!\d)")

NER_RULES = {
    "PERSON": ("Person name", "low"),
    "GPE": ("Location", "medium"),
    "LOC": ("Location", "medium"),
    "ORG": ("Organisation (school/work)", "medium"),
    "DATE": ("Date", "low"),
}

DOB_HINTS = re.compile(r"\b(born|birthday|bday|b'day|dob|date of birth)\b", re.I)
ADDRESS_HINTS = re.compile(
    r"\b(i live (in|at|near)|my address|house no|flat no|my home is|staying at)\b", re.I)
PIN_CONTEXT = re.compile(r"pin\s?code|pincode|\bpin\b|postal|\bzip\b|\bpo\b", re.I)
ORG_CONTEXT = re.compile(
    r"\b(?:at|joined|joining|from|(?:work|works|worked|working)\s+(?:at|for)|"
    r"(?:study|studies|studied|studying)\s+(?:at|in))\s+(?:the\s+)?$", re.I)
# Phrases that can only be followed by an employer/school, even if spaCy calls it a person
EMPLOYER_CUE = re.compile(
    r"\b(?:joined|joining|(?:work|works|worked|working)\s+(?:at|for)|(?:intern|interning|interned)\s+(?:at|with)|"
    r"job\s+(?:at|in))\s+$", re.I)
NAME_CUE = re.compile(r"(?:\bi'?m|\bi am|my name is|name'?s|this is|called|thanks to|thanks|\bhi|hello|\bhey)\s*,?\s*$", re.I)
DURATION = re.compile(r"\b(day|week|month|year|hour|minute)s?\b|\b(today|tomorrow|yesterday|tonight)\b", re.I)

SENSITIVE_TYPES = ("Email address", "Aadhaar number", "PAN number", "Phone number")
CURRENT_YEAR = date.today().year


def mask(value: str, kind: str) -> str:
    """Hide the middle of very sensitive values so reports are safe to share."""
    if kind in ("Phone number", "Aadhaar number", "PAN number"):
        chars = value.strip()
        if len(chars) > 6:
            return chars[:2] + "*" * (len(chars) - 6) + chars[-4:]
    if kind == "Email address" and "@" in value:
        user, domain = value.split("@", 1)
        return user[:2] + "***@" + domain
    return value


def redact(text: str) -> str:
    """Mask phone/Aadhaar/PAN/email inside a sentence before showing it."""
    for kind, pattern, _, _ in ID_RULES:
        if kind in SENSITIVE_TYPES:
            text = pattern.sub(lambda m, k=kind: mask(m.group(), k), text)
    return text


def canonical(kind: str, value: str) -> str:
    """Normal form of a value, so different spellings of the same thing merge."""
    if kind == "Phone number":
        return re.sub(r"\D", "", value)[-10:]
    if kind in ("Aadhaar number", "PAN number", "Vehicle number"):
        return re.sub(r"[\s-]", "", value).upper()
    return re.sub(r"\s+", " ", value.strip().lower())


def _sentence_before(text: str, start: int, end: int) -> str:
    """Text from the start of the sentence up to the end of the match."""
    boundary = max(text.rfind(c, 0, start) for c in ".!?\n")
    return text[boundary + 1:end]


def _overlaps(span, taken):
    return any(span[0] < end and start < span[1] for start, end in taken)


def _year_in(value: str) -> int | None:
    m = re.search(r"(?:19|20)\d{2}", value)
    if m:
        return int(m.group())
    m = re.search(r"[/.-](\d{2})$", value)        # dd/mm/yy
    if m:
        yy = int(m.group(1))
        return 1900 + yy if yy > CURRENT_YEAR % 100 else 2000 + yy
    return None


def _pin_has_context(text: str, start: int, end: int) -> bool:
    before = text[max(0, start - 35):start]
    return bool(PIN_CONTEXT.search(before) or PLACE_RE.search(before)
                or ADDRESS_HINTS.search(_sentence_before(text, start, end)))


def detect_pii(text: str) -> list[Finding]:
    return detect_pii_with_spans(text)[0]


def detect_pii_with_spans(text: str) -> tuple[list[Finding], list[tuple[int, int]]]:
    """Findings plus the character spans they cover (used to avoid double-counting)."""
    findings: list[Finding] = []
    by_key: dict[tuple[str, str], Finding] = {}
    taken: list[tuple[int, int]] = []   # character spans already reported

    def add(kind, value, severity, source, span, confidence):
        taken.append(span)
        key = (kind, canonical(kind, value))
        if key in by_key:
            by_key[key].occurrences += 1
            return
        why, fix = describe(kind)
        finding = Finding(category="pii", type=kind, value=mask(value, kind), severity=severity,
                          source=source, confidence=confidence, explanation=why, fix=fix)
        by_key[key] = finding
        findings.append(finding)

    # 1) Regex layer: fixed-format identifiers
    for kind, pattern, severity, confidence in ID_RULES:
        for m in pattern.finditer(text):
            if not _overlaps(m.span(), taken):
                add(kind, m.group(), severity, "regex", m.span(), confidence)

    # 2) Dates: a date is a birth date only when the sentence says so
    for pattern in DATE_RULES:
        for m in pattern.finditer(text):
            span = m.span()
            if _overlaps(span, taken):
                continue
            year = _year_in(m.group())
            if DOB_HINTS.search(_sentence_before(text, *span)):
                if year is None or year <= CURRENT_YEAR:
                    add("Date of birth", m.group(), "high", "regex + context", span, 0.85)
            elif year and CURRENT_YEAR - 60 <= year <= CURRENT_YEAR - 10:
                add("Date (possible DOB)", m.group(), "low", "regex", span, 0.4)

    # 3) PIN codes: only with an address-like context
    for m in PIN_RE.finditer(text):
        if not _overlaps(m.span(), taken) and _pin_has_context(text, *m.span()):
            add("PIN code", m.group(), "medium", "regex + context", m.span(), 0.7)

    # 4) AI layer: spaCy named entities, filtered
    doc = get_nlp()(text)
    for ent in doc.ents:
        if ent.label_ not in NER_RULES:
            continue
        span = (ent.start_char, ent.end_char)
        if _overlaps(span, taken):
            continue
        kind, severity = NER_RULES[ent.label_]
        words = [t.text.lower() for t in ent]
        before = text[max(0, ent.start_char - 30):ent.start_char]

        if ent.label_ == "DATE":
            context = _sentence_before(text, ent.start_char, ent.end_char)
            year = _year_in(ent.text)
            if (DOB_HINTS.search(context) and not DURATION.search(ent.text)
                    and (year is None or year <= CURRENT_YEAR) and re.search(r"\d", ent.text)):
                add("Date of birth", ent.text.strip(), "high", "spaCy NER + context", span, 0.7)
            continue

        if any(w in NOT_ENTITIES for w in words) or any(ch.isdigit() for ch in ent.text):
            continue
        if not any(t.pos_ in ("PROPN", "NOUN") for t in ent):
            continue   # junk entities such as "Going to"

        if ent.label_ in ("GPE", "LOC"):
            known = ent.text.lower() in PLACE_SET
            if ent.text.lower() in COUNTRIES or not (known or ent.text[0].isupper()):
                continue   # countries are not identifying; lowercase words like "hai" are noise
            add(kind, ent.text.strip(), severity, "spaCy NER", span, 0.9 if known else 0.6)
        elif ent.label_ == "PERSON":
            if not all(w[0].isupper() for w in ent.text.split()):
                continue
            if words[0] in ("joined", "joining") and len(words) > 1:   # spaCy folded the verb into the name
                add("Organisation (school/work)", ent.text.split(None, 1)[1], "medium",
                    "spaCy NER + context", span, 0.55)
                continue
            if EMPLOYER_CUE.search(before):   # "interning at Wipro": a company, not a person
                add("Organisation (school/work)", ent.text.strip(), "medium", "spaCy NER + context", span, 0.55)
                continue
            if len(ent) < 2 and not NAME_CUE.search(before):
                continue   # a lone capitalised word is too ambiguous
            add(kind, ent.text.strip(), severity, "spaCy NER", span, 0.65 if len(ent) > 1 else 0.55)
        elif ent.label_ == "ORG":
            if ORG_CONTEXT.search(before):   # only after "at / joined / working at ..."
                add(kind, ent.text.strip(), severity, "spaCy NER + context", span, 0.55)

    # 5) Phrases that reveal a home address
    for m in ADDRESS_HINTS.finditer(text):
        snippet = re.split(r"[\n!?]|\.\s", text[m.start():m.end() + 40])[0].strip()
        add("Home address hint", redact(snippet), "high", "keyword rule", m.span(), 0.75)

    return findings, taken
