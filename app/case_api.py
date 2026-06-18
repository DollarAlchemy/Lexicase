"""case_api.py — the seam between the UI and case data on disk.

THE ONE RULE: the UI talks only to these functions. It never reads or writes
case files directly. That keeps the file browser, the forms, and the document
generator decoupled — each later build step plugs in *here* instead of reaching
into another module.

A "case" lives as a folder under the workspace:

    workspace/
        Smith-v-Acme/
            case.json          # metadata: status, dates, deadlines
            client.json        # the client form, as data
            defendant.json     # the defendant form, as data
            contacts.json
            evidence/document/  evidence/image/  evidence/video/
            court-outputs/
            generated/         # documents produced from templates (Step 5)

Step 2 (this file) implements: create_case, list_cases, load_case_meta,
read_form, write_form, and list_case_files. generate_document arrives in Step 5.
"""
from __future__ import annotations

import json
from pathlib import Path

from app import schemas

# Workspace lives at <project>/workspace and is git-ignored — real case data
# (SSNs, etc.) never lands in version control.
WORKSPACE = Path(__file__).resolve().parent.parent / "workspace"

CASE_META = "case.json"
SUBFOLDERS = [
    "evidence/document",
    "evidence/image",
    "evidence/video",
    "court-outputs",
    "generated",
]


# ---- workspace + paths -----------------------------------------------------
def ensure_workspace(workspace: Path | None = None) -> Path:
    ws = Path(workspace) if workspace else WORKSPACE
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def case_dir(name: str, workspace: Path | None = None) -> Path:
    return ensure_workspace(workspace) / name


# ---- small JSON helpers ----------------------------------------------------
def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ---- the public API the UI calls -------------------------------------------
def list_cases(workspace: Path | None = None) -> list[str]:
    """Names of every case folder (a folder containing case.json), sorted."""
    ws = ensure_workspace(workspace)
    return sorted(
        p.name for p in ws.iterdir() if p.is_dir() and (p / CASE_META).exists()
    )


def create_case(name: str, workspace: Path | None = None) -> Path:
    """Create a new case folder with its skeleton + starter JSON files."""
    cdir = case_dir(name, workspace)
    if cdir.exists():
        raise FileExistsError(f"Case already exists: {name}")
    for sub in SUBFOLDERS:
        (cdir / sub).mkdir(parents=True, exist_ok=True)
    _write_json(cdir / CASE_META, schemas.case_meta(name))
    _write_json(cdir / "client.json", schemas.client_form())
    _write_json(cdir / "defendant.json", schemas.defendant_form())
    _write_json(cdir / "contacts.json", schemas.contacts_file())
    return cdir


def load_case_meta(name: str, workspace: Path | None = None) -> dict | None:
    """Read case.json, or None if the case doesn't exist."""
    p = case_dir(name, workspace) / CASE_META
    return _read_json(p) if p.exists() else None


def read_form(name: str, form: str, workspace: Path | None = None) -> dict:
    """Read a form's JSON into a dict; return an empty form if not yet written."""
    if form not in schemas.FORMS:
        raise ValueError(f"Unknown form '{form}'. Known: {list(schemas.FORMS)}")
    p = case_dir(name, workspace) / f"{form}.json"
    return _read_json(p) if p.exists() else schemas.FORMS[form]()


def write_form(name: str, form: str, data: dict, workspace: Path | None = None) -> None:
    """Write a form dict back to its JSON file."""
    if form not in schemas.FORMS:
        raise ValueError(f"Unknown form '{form}'. Known: {list(schemas.FORMS)}")
    _write_json(case_dir(name, workspace) / f"{form}.json", data)


def list_templates() -> list[tuple[str, str]]:
    """Available document templates as (template_id, human_label) pairs."""
    from app import documents
    return [(tid, label) for tid, (_b, _s, label) in documents.TEMPLATES.items()]


def export_case(name: str, dest_zip: Path, workspace: Path | None = None) -> Path:
    """Zip a case folder into dest_zip and return the written archive path."""
    import shutil

    src = case_dir(name, workspace)
    if not src.exists():
        raise FileNotFoundError(f"No such case: {name}")
    base = Path(dest_zip).with_suffix("")  # make_archive appends .zip itself
    archive = shutil.make_archive(str(base), "zip", root_dir=str(src))
    return Path(archive)


def list_case_files(name: str, workspace: Path | None = None) -> dict:
    """Return the case's file tree as nested dicts (folder -> children, file -> None).

    Implemented now; wired into the file-browser widget in Step 3.
    """
    root = case_dir(name, workspace)

    def walk(p: Path) -> dict:
        node: dict = {}
        for child in sorted(p.iterdir(), key=lambda c: (c.is_file(), c.name.lower())):
            node[child.name] = walk(child) if child.is_dir() else None
        return node

    return walk(root) if root.exists() else {}


def generate_document(name: str, template: str = "client_intake", workspace: Path | None = None) -> Path:
    """Merge a case's data into a template -> generated/<file>.pdf. The money-shot.

    Returns the path to the written PDF. Stays the only doorway to disk: the UI
    calls this, never reportlab directly.
    """
    from datetime import datetime

    from app import documents

    if template not in documents.TEMPLATES:
        raise ValueError(f"Unknown template '{template}'. Known: {list(documents.TEMPLATES)}")
    builder, stem, _label = documents.TEMPLATES[template]

    # Hand every builder the whole case, read through the seam; each uses what it needs.
    bundle = {
        "client": read_form(name, "client", workspace),
        "defendant": read_form(name, "defendant", workspace),
        "contacts": read_form(name, "contacts", workspace),
        "meta": load_case_meta(name, workspace) or {},
    }

    gen_dir = case_dir(name, workspace) / "generated"
    gen_dir.mkdir(parents=True, exist_ok=True)
    out = gen_dir / f"{stem}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.pdf"
    builder(name, bundle, out)
    return out
