from app.services.pii_detector import detect_pii, detect_pii_with_spans, mask, redact
from app.services.text_risk_model import analyze_content


def types_found(text):
    return {f.type for f in detect_pii(text)}


def test_detects_phone_email_and_dob():
    found = types_found("Call 9876543210 or mail rahul.s@gmail.com. Born 12/05/2004")
    assert {"Phone number", "Email address", "Date of birth"} <= found


def test_detects_indian_ids():
    found = types_found("Aadhaar 1234 5678 9012, PAN ABCDE1234F, car DL 3C AB 1234")
    assert {"Aadhaar number", "PAN number", "Vehicle number"} <= found


def test_detects_places_and_college():
    found = types_found("Studying at IIT Kanpur, from Lucknow")
    assert {"Organisation (school/work)", "Location"} <= found


def test_durations_are_not_birthdays():
    text = "Born in 2004. Going to Goa for 2 weeks."
    assert all(f.value != "2 weeks" for f in detect_pii(text))
    assert "Location" in types_found(text)


def test_safe_text_has_no_findings():
    assert detect_pii("Loved the new Batman movie. Coding all night, coffee is life.") == []


def test_masking():
    assert mask("9876543210", "Phone number") == "98****3210"
    assert "9876543210" not in redact("call me at 9876543210")


def test_ml_model_separates_risky_and_safe():
    risky, _ = analyze_content("Going on vacation for two weeks, house will be empty")
    safe, _ = analyze_content("Learning machine learning is fun")
    assert risky > 60 > safe


# --- regression tests for bugs found during the accuracy review ---------------------------------

def test_same_phone_in_different_formats_is_one_finding():
    findings = [f for f in detect_pii("Call 9876543210. WhatsApp: 98765 43210 or +91 9876543210")
                if f.type == "Phone number"]
    assert len(findings) == 1 and findings[0].occurrences == 3


def test_six_digit_numbers_are_not_pin_codes_without_context():
    assert "PIN code" not in types_found("I scored 100000 points and have 250000 followers")
    assert "PIN code" in types_found("My pincode is 110024")
    assert "PIN code" in types_found("I live in Lajpat Nagar, New Delhi 110024")


def test_lowercase_noise_is_not_a_location():
    found = [f.value for f in detect_pii("mera number 9876543210 hai, ghar Lucknow mein hai") if f.type == "Location"]
    assert found == ["Lucknow"]


def test_app_names_are_not_organisations_or_people():
    assert detect_pii("Message me on WhatsApp or Instagram. Follow me on Snapchat and YouTube") == []


def test_future_or_plain_dates_are_not_birthdays():
    assert detect_pii("Exam is on 12/05/2026, meeting on 3 March") == []
    assert "Date of birth" in types_found("Born on 12/05/2004")


def test_organisation_only_after_an_employer_or_school_cue():
    assert "Organisation (school/work)" in types_found("Joined Wipro last month as an analyst")
    assert "Organisation (school/work)" not in types_found("Learning Python and React this semester")


def test_every_finding_explains_itself():
    for f in detect_pii("Call 9876543210, born 12/05/2004, going to Goa, studying at IIT Kanpur"):
        assert f.explanation and f.fix and 0 < f.confidence <= 1


def test_fixed_format_ids_are_more_confident_than_ner_guesses():
    by_type = {f.type: f.confidence for f in detect_pii("Call 9876543210, going to Goa, hi I'm Rahul Sharma")}
    assert by_type["Phone number"] > by_type["Person name"]


def test_sentence_explained_by_pii_is_not_counted_twice_by_the_ml_model():
    text = "Born 12/05/2004."
    _, spans = detect_pii_with_spans(text)
    assert analyze_content(text, spans)[1] == []
