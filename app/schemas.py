"""schemas.py — the shape of case data, in one place.

Every form is a flat dict with a `schemaVersion`. Keeping the shapes here (not
scattered through the code) means: the data model is documented in one file, and
when a shape changes you bump SCHEMA_VERSION and migrate in one place.

Fields mirror the client/defendant forms from the project brief.
"""
from __future__ import annotations

from datetime import date

SCHEMA_VERSION = 1


def client_form() -> dict:
    """An empty client form."""
    return {
        "schemaVersion": SCHEMA_VERSION,
        "name": "",
        "dob": "",
        "address": "",
        "ssn": "",
        "militaryStatus": "",
        "dateOfContact": "",
        "dateOfHire": "",
        "dateOfFarewell": "",
        "occupation": "",
        "location": "",
        "boss": "",
        "income": "",
        "vehicle": "",
        "ids": "",
        "licenses": "",
        "majorAssets": "",
        "statementOfIncident": "",
        "evidenceAndFacts": "",
        "legalProcessTimeline": "",
        "supporters": "",
    }


def defendant_form() -> dict:
    """An empty defendant form."""
    return {
        "schemaVersion": SCHEMA_VERSION,
        "name": "",
        "address": "",
    }


def contacts_file() -> dict:
    """An empty contacts list."""
    return {
        "schemaVersion": SCHEMA_VERSION,
        "contacts": [],  # each: {"name","role","email","phone"}
    }


def case_meta(name: str) -> dict:
    """Metadata for a new case (case.json)."""
    return {
        "schemaVersion": SCHEMA_VERSION,
        "caseName": name,
        "status": "active",            # active | closed
        "createdDate": date.today().isoformat(),
        "deadlines": [],               # each: {"label","date"} — used in Phase 2
    }


# Maps a form name -> the factory that builds its empty version.
# read_form / write_form validate against these keys.
FORMS = {
    "client": client_form,
    "defendant": defendant_form,
    "contacts": contacts_file,
}

# How each form renders in the UI: (json_key, label, widget_kind).
# kind is "line" (single-line) or "text" (multi-line). The form editor loops
# over this spec, so adding a field here updates the form automatically.
FIELD_SPECS = {
    "client": [
        ("name", "Name", "line"),
        ("dob", "Date of birth", "line"),
        ("address", "Address", "text"),
        ("ssn", "SSN", "line"),
        ("militaryStatus", "Military status", "line"),
        ("dateOfContact", "Date of contact", "line"),
        ("dateOfHire", "Date of hire", "line"),
        ("dateOfFarewell", "Date of farewell", "line"),
        ("occupation", "Occupation", "line"),
        ("location", "Location", "line"),
        ("boss", "Boss", "line"),
        ("income", "Income", "line"),
        ("vehicle", "Vehicle", "line"),
        ("ids", "IDs", "line"),
        ("licenses", "Licenses", "line"),
        ("majorAssets", "Major assets", "text"),
        ("statementOfIncident", "Statement of incident", "text"),
        ("evidenceAndFacts", "Evidence & facts", "text"),
        ("legalProcessTimeline", "Legal process timeline", "text"),
        ("supporters", "Supporters", "text"),
    ],
    "defendant": [
        ("name", "Name", "line"),
        ("address", "Address", "text"),
    ],
}
