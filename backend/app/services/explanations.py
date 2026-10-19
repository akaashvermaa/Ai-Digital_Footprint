"""Plain-language "why is this risky?" and "what should I do?" for every finding type.

Kept in one place so the detector, the recommendations and the PDF all say the same thing.
"""

# type -> (why it is risky, what to do)
CATALOGUE = {
    "Phone number": (
        "Anyone can call or message you, and phone numbers are used to reset passwords and for SIM-swap or spam-call scams.",
        "Remove your phone number from public bios and posts; share it only in private messages."),
    "Email address": (
        "Public emails collect spam and phishing, and link your accounts together.",
        "Avoid posting your email publicly; use a separate email for social media sign-ups."),
    "Aadhaar number": (
        "Aadhaar is a core identity document. With it, someone can attempt identity fraud or SIM and loan misuse.",
        "Never share your Aadhaar number online. Use a masked Aadhaar or Virtual ID where possible."),
    "PAN number": (
        "PAN is tied to your finances; it can be misused for tax or loan fraud.",
        "Remove your PAN number from public posts."),
    "Date of birth": (
        "Your birth date is used to verify identity and is a common password and security-question answer.",
        "Hide your date of birth, or show only the day and month."),
    "Date (possible DOB)": (
        "This looks like it could be a birth date. If it is, it helps identity theft and password guessing.",
        "Check whether this date is your birthday, and hide it if so."),
    "Vehicle number": (
        "A number plate can be traced to its owner and used to find where you live or park.",
        "Blur number plates in photos and avoid posting them."),
    "PIN code": (
        "Your area PIN code narrows down where you live.",
        "Avoid sharing your PIN code together with other address details."),
    "Home address hint": (
        "Saying where you live or stay lets strangers find your home.",
        "Never reveal where you live publicly; share addresses only with trusted people privately."),
    "Location": (
        "Named places show where you live, study or travel, which helps stalking and burglary planning.",
        "Avoid tagging exact locations; post travel photos after you return."),
    "Organisation (school/work)": (
        "Your school or workplace tells strangers where to find you in person and helps them target you.",
        "Consider hiding your school or workplace on public profiles."),
    "Person name": (
        "A full name makes it easy to search for you across the web and link your accounts.",
        "Use a nickname on public profiles if possible."),
    "Link / URL": (
        "Links can lead to other profiles that expose more information.",
        "Check that linked profiles don't expose more personal information."),
    "Risky post": (
        "Posts like this reveal routines, travel plans, documents or secrets that others can misuse.",
        "Delete or make private the posts flagged as risky; share such updates only with close friends."),
}


def describe(finding_type: str) -> tuple[str, str]:
    """(why, fix) for a finding type; ML findings are named 'Risky post (xx% confidence)'."""
    key = "Risky post" if finding_type.startswith("Risky post") else finding_type
    return CATALOGUE.get(key, ("", ""))
