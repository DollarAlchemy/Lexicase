"""check_data_layer.py — proves Step 2 works, and seeds a sample case.

Run it from the project root:
    python tools/check_data_layer.py

It will: create a sample case (if missing), write some client data, read it
back, list cases, and print PASS. Afterwards the sample case shows up in the
CASES panel when you run the app.
"""
import sys
from pathlib import Path

# Make `app` importable when this script is run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import case_api  # noqa: E402

SAMPLE = "Smith-v-Acme"


def main() -> int:
    # 1. create the sample case if it isn't there yet
    if SAMPLE not in case_api.list_cases():
        case_api.create_case(SAMPLE)
        print(f"created case: {SAMPLE}")
    else:
        print(f"case already exists: {SAMPLE}")

    # 2. write some client data through the seam
    client = case_api.read_form(SAMPLE, "client")
    client["name"] = "Jordan Smith"
    client["dob"] = "1990-04-12"
    client["occupation"] = "Logistics coordinator"
    client["statementOfIncident"] = "Wrongful termination following a reported safety violation."
    case_api.write_form(SAMPLE, "client", client)
    print("wrote client.json")

    # 3. read it back and verify the round-trip
    again = case_api.read_form(SAMPLE, "client")
    assert again["name"] == "Jordan Smith", "round-trip failed: name"
    assert again["schemaVersion"] == 1, "round-trip failed: schemaVersion"
    print(f"read back -> name={again['name']!r}, occupation={again['occupation']!r}")

    # 4. metadata + roster
    meta = case_api.load_case_meta(SAMPLE)
    print(f"case.json -> status={meta['status']}, created={meta['createdDate']}")
    print(f"list_cases() -> {case_api.list_cases()}")

    print("\nPASS — the data layer round-trips. Step 2 is solid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
