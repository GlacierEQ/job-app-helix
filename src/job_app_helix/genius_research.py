"""Mandatory research/study phase + lite knowledge accumulation for Genius Engine.

Every invent run starts here. Study accumulates into:
  - helix machine/genius_knowledge/ (local lite store)
  - optional GlacierEQ/library-of-links (organized link registry)

Network research uses `gh` when available; offline/subject signals always apply.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RESEARCH_SCHEMA = "glaciereq.genius-research.v1"
KNOWLEDGE_SCHEMA = "glaciereq.genius-lite-knowledge.v1"
LINK_SCHEMA = "glaciereq.library-of-links.entry.v1"


class ResearchError(ValueError):
    """Research phase could not produce a usable dossier."""


@dataclass(frozen=True)
class ResearchDossier:
    """Leaf-native study packet — mandatory invent input."""

    schema: str
    repository: str
    full_name: str
    description: str
    primary_language: str
    languages: dict[str, int]
    topics: tuple[str, ...]
    readme_excerpt: str
    default_branch: str
    exists: bool
    signals: tuple[str, ...]
    lite_facts: tuple[str, ...]
    prior_run_count: int
    prior_primary_mechanism: str
    sources: tuple[str, ...]
    researched_at: str
    raw_subject: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["topics"] = list(self.topics)
        payload["signals"] = list(self.signals)
        payload["lite_facts"] = list(self.lite_facts)
        payload["sources"] = list(self.sources)
        return payload


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _repo_slug(repository: str) -> str:
    name = repository.strip()
    if name.startswith("https://github.com/"):
        name = name.removeprefix("https://github.com/").removesuffix(".git")
    return name.strip("/")


def _safe_key(repository: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "__", _repo_slug(repository))


def knowledge_root(helix_root: Path) -> Path:
    return helix_root / "machine" / "genius_knowledge"


def library_of_links_root() -> Path | None:
    """Resolve library-of-links working tree if configured or checked out beside helix."""
    env = os.environ.get("GENIUS_LIBRARY_OF_LINKS_ROOT") or os.environ.get(
        "LIBRARY_OF_LINKS_ROOT"
    )
    if env:
        path = Path(env).expanduser()
        if path.is_dir():
            return path
    # common sibling checkouts
    here = Path(__file__).resolve()
    candidates = [
        here.parents[3] / "library-of-links",
        Path.home() / ".grok" / "work" / "library-of-links",
        Path.home() / "GlacierEQ_Swarm" / "library-of-links",
    ]
    for path in candidates:
        if path.is_dir():
            return path
    return None


def _run_gh_json(args: Sequence[str], timeout: float = 25.0) -> Any | None:
    try:
        proc = subprocess.run(
            ["gh", *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def fetch_github_surface(repository: str) -> dict[str, Any]:
    """Live GH surface — empty dict when offline / missing."""
    full = _repo_slug(repository)
    if "/" not in full:
        full = f"GlacierEQ/{full}"
    meta = _run_gh_json(
        [
            "api",
            f"repos/{full}",
            "--jq",
            (
                "{full_name,description,language,default_branch,private,archived,"
                "stargazers_count,open_issues_count,topics,pushed_at,size}"
            ),
        ]
    )
    if not isinstance(meta, dict):
        return {"full_name": full, "exists": False}

    langs = _run_gh_json(["api", f"repos/{full}/languages"])
    if not isinstance(langs, dict):
        langs = {}

    readme = ""
    readme_payload = _run_gh_json(["api", f"repos/{full}/readme", "--jq", ".content"])
    if isinstance(readme_payload, str) and readme_payload:
        import base64

        try:
            raw = base64.b64decode(readme_payload).decode("utf-8", errors="replace")
            readme = raw[:2500]
        except Exception:
            readme = ""

    return {
        "full_name": meta.get("full_name") or full,
        "exists": True,
        "description": str(meta.get("description") or ""),
        "language": str(meta.get("language") or ""),
        "default_branch": str(meta.get("default_branch") or "main"),
        "topics": list(meta.get("topics") or []),
        "languages": {str(k): int(v) for k, v in langs.items()},
        "readme_excerpt": readme,
        "private": bool(meta.get("private")),
        "archived": bool(meta.get("archived")),
        "pushed_at": meta.get("pushed_at"),
        "size": meta.get("size"),
        "open_issues_count": meta.get("open_issues_count"),
    }


def load_prior_knowledge(helix_root: Path, repository: str) -> dict[str, Any]:
    path = knowledge_root(helix_root) / f"{_safe_key(repository)}.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def derive_signals(
    subject: Mapping[str, Any],
    surface: Mapping[str, Any],
    prior: Mapping[str, Any],
) -> tuple[str, ...]:
    signals: list[str] = []
    text = " ".join(
        [
            str(subject.get("repository") or ""),
            str(subject.get("description") or surface.get("description") or ""),
            str(surface.get("readme_excerpt") or "")[:800],
            " ".join(str(t) for t in (surface.get("topics") or [])),
        ]
    ).lower()

    if int(subject.get("neutralization_stamps") or 0) >= 2:
        signals.append("neutralization")
    if subject.get("paper_recovery_only"):
        signals.append("paper_recovery")
    if subject.get("hollow_or_thin"):
        signals.append("hollow")
    if subject.get("missing_implementation"):
        signals.append("missing_impl")

    if not surface.get("exists"):
        signals.append("unknown_or_offline")
    if surface.get("archived"):
        signals.append("archived")
    if surface.get("size") is not None and int(surface.get("size") or 0) < 40:
        signals.append("tiny_repo")
    # Avoid false positives from repo name fragments; require word-ish markers.
    if re.search(r"\b(pytest|unittest|ci/cd|github actions|test suite|tests/)\b", text) or (
        " test" in f" {text}" or text.startswith("test")
    ):
        signals.append("mentions_tests")
    else:
        signals.append("no_test_mention")
    if any(k in text for k in ("mvp", "scaffold", "stub", "placeholder", "todo")):
        signals.append("scaffold_language")
    if any(k in text for k in ("telemetry", "sensor", "stream")):
        signals.append("telemetry")
    if any(k in text for k in ("cooling", "thermal", "energy", "colossus")):
        signals.append("thermal_energy")
    if any(k in text for k in ("mcp", "stdio", "tool")):
        signals.append("mcp_tools")
    if any(k in text for k in ("orbital", "lambert", "kepler", "astrodynamic")):
        signals.append("orbital")
    if any(k in text for k in ("babel", "polyglot", "language")):
        signals.append("polyglot")
    if any(k in text for k in ("agent", "orchestr", "mesh", "registry")):
        signals.append("agent_mesh")
    if any(k in text for k in ("governance", "akos", "authority", "provenance")):
        signals.append("governance")
    if any(k in text for k in ("hire", "resume", "portfolio", "recruiter")):
        signals.append("hire_surface")
    if prior.get("run_count"):
        signals.append("has_prior_knowledge")
    if prior.get("last_primary_mechanism_id"):
        signals.append("prior_mechanism_known")

    # de-dupe preserve order
    seen: set[str] = set()
    ordered: list[str] = []
    for s in signals:
        if s not in seen:
            seen.add(s)
            ordered.append(s)
    return tuple(ordered)


def derive_lite_facts(
    subject: Mapping[str, Any],
    surface: Mapping[str, Any],
    signals: Sequence[str],
) -> tuple[str, ...]:
    facts: list[str] = []
    full = str(surface.get("full_name") or subject.get("repository") or "")
    if full:
        facts.append(f"repo:{full}")
    lang = surface.get("language") or subject.get("language")
    if lang:
        facts.append(f"primary_language:{lang}")
    langs = surface.get("languages") or {}
    if isinstance(langs, dict) and langs:
        top = sorted(langs.items(), key=lambda kv: -int(kv[1]))[:3]
        facts.append("languages:" + ",".join(f"{k}:{v}" for k, v in top))
    desc = (surface.get("description") or subject.get("description") or "").strip()
    if desc:
        facts.append(f"description:{desc[:160]}")
    for sig in signals[:12]:
        facts.append(f"signal:{sig}")
    topics = surface.get("topics") or []
    for t in list(topics)[:6]:
        facts.append(f"topic:{t}")
    return tuple(facts)


def research_subject(
    subject: Mapping[str, Any],
    *,
    helix_root: Path | None = None,
    live: bool = True,
) -> ResearchDossier:
    """Mandatory study phase — always runs before invent."""
    if not isinstance(subject, Mapping) or not subject:
        raise ResearchError("subject must be a non-empty mapping")
    repo = str(subject.get("repository") or subject.get("name") or "").strip()
    if not repo:
        raise ResearchError("subject.repository is required for research")

    root = helix_root or Path(__file__).resolve().parents[2]
    prior = load_prior_knowledge(root, repo)
    surface: dict[str, Any]
    sources: list[str] = ["subject_fields"]
    if live and not subject.get("offline") and not os.environ.get("GENIUS_OFFLINE"):
        surface = fetch_github_surface(repo)
        sources.append("github_api" if surface.get("exists") else "github_miss")
    else:
        surface = {
            "full_name": _repo_slug(repo) if "/" in repo else f"GlacierEQ/{repo}",
            "exists": False,
            "description": str(subject.get("description") or ""),
            "language": str(subject.get("language") or ""),
            "default_branch": "main",
            "topics": list(subject.get("topics") or []),
            "languages": dict(subject.get("languages") or {}),
            "readme_excerpt": str(subject.get("readme_excerpt") or ""),
        }
        sources.append("offline_or_forced")

    # fold explicit subject overrides
    if subject.get("description"):
        surface["description"] = str(subject["description"])
    if subject.get("readme_excerpt"):
        surface["readme_excerpt"] = str(subject["readme_excerpt"])
    if subject.get("topics"):
        surface["topics"] = list(subject["topics"])  # type: ignore[assignment]
    if subject.get("languages"):
        surface["languages"] = dict(subject["languages"])  # type: ignore[assignment]

    sources.append("prior_knowledge" if prior else "no_prior_knowledge")
    signals = derive_signals(subject, surface, prior)
    facts = derive_lite_facts(subject, surface, signals)

    return ResearchDossier(
        schema=RESEARCH_SCHEMA,
        repository=repo,
        full_name=str(surface.get("full_name") or repo),
        description=str(surface.get("description") or ""),
        primary_language=str(surface.get("language") or subject.get("language") or "unknown"),
        languages={str(k): int(v) for k, v in (surface.get("languages") or {}).items()},
        topics=tuple(str(t) for t in (surface.get("topics") or [])),
        readme_excerpt=str(surface.get("readme_excerpt") or "")[:2500],
        default_branch=str(surface.get("default_branch") or "main"),
        exists=bool(surface.get("exists")),
        signals=signals,
        lite_facts=facts,
        prior_run_count=int(prior.get("run_count") or 0),
        prior_primary_mechanism=str(prior.get("last_primary_mechanism_id") or ""),
        sources=tuple(sources),
        researched_at=_utc_now(),
        raw_subject=dict(subject),
    )


def accumulate_knowledge(
    dossier: ResearchDossier,
    *,
    helix_root: Path,
    primary: Mapping[str, Any] | None,
    receipt_sha256: str,
) -> Path:
    """Persist lite knowledge for this leaf — accumulates across runs."""
    store = knowledge_root(helix_root)
    store.mkdir(parents=True, exist_ok=True)
    key = _safe_key(dossier.repository)
    path = store / f"{key}.json"
    prior = load_prior_knowledge(helix_root, dossier.repository)
    history = list(prior.get("history") or [])
    entry = {
        "researched_at": dossier.researched_at,
        "receipt_sha256": receipt_sha256,
        "signals": list(dossier.signals),
        "primary_mechanism_id": (primary or {}).get("tags", [None])[0]
        if primary
        else None,
        "primary_title": (primary or {}).get("title"),
        "genius_score": (primary or {}).get("genius_score"),
        "lite_facts": list(dossier.lite_facts)[:20],
    }
    # prefer mechanism id from tags first element if string
    if primary and isinstance(primary.get("tags"), list) and primary["tags"]:
        entry["primary_mechanism_id"] = primary["tags"][0]
    history.append(entry)
    history = history[-40:]  # light cap
    payload = {
        "schema": KNOWLEDGE_SCHEMA,
        "repository": dossier.repository,
        "full_name": dossier.full_name,
        "run_count": int(prior.get("run_count") or 0) + 1,
        "last_primary_mechanism_id": entry.get("primary_mechanism_id"),
        "last_receipt_sha256": receipt_sha256,
        "signals_union": sorted(
            set(list(prior.get("signals_union") or []) + list(dossier.signals))
        ),
        "lite_facts": list(dossier.lite_facts),
        "description": dossier.description,
        "primary_language": dossier.primary_language,
        "updated_at": _utc_now(),
        "history": history,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # index
    index_path = store / "index.json"
    index: dict[str, Any]
    if index_path.is_file():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            index = {"schema": KNOWLEDGE_SCHEMA, "entries": {}}
    else:
        index = {"schema": KNOWLEDGE_SCHEMA, "entries": {}}
    entries = index.setdefault("entries", {})
    entries[dossier.full_name or dossier.repository] = {
        "path": path.name,
        "run_count": payload["run_count"],
        "updated_at": payload["updated_at"],
        "last_primary_mechanism_id": payload["last_primary_mechanism_id"],
    }
    index["updated_at"] = _utc_now()
    index["count"] = len(entries)
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def publish_library_link(
    dossier: ResearchDossier,
    *,
    primary: Mapping[str, Any] | None,
    receipt_sha256: str,
    library_root: Path | None = None,
) -> Path | None:
    """Append/update organized link entry in library-of-links repo tree."""
    root = library_root if library_root is not None else library_of_links_root()
    if root is None:
        return None
    registry = root / "registry"
    domains = root / "domains" / "genius"
    knowledge = root / "knowledge" / "lite"
    for path in (registry, domains, knowledge):
        path.mkdir(parents=True, exist_ok=True)

    full = dossier.full_name or dossier.repository
    url = f"https://github.com/{full}" if "/" in full else full
    link_id = _safe_key(full)
    entry = {
        "schema": LINK_SCHEMA,
        "id": link_id,
        "url": url,
        "title": full,
        "description": dossier.description,
        "domain": "genius",
        "tags": list(dossier.signals) + list(dossier.topics),
        "primary_language": dossier.primary_language,
        "lite_knowledge": list(dossier.lite_facts),
        "last_genius_primary": (primary or {}).get("title"),
        "last_mechanism_id": (
            (primary or {}).get("tags", [None])[0] if primary else None
        ),
        "last_receipt_sha256": receipt_sha256,
        "updated_at": _utc_now(),
        "sources": list(dossier.sources),
    }
    if primary and isinstance(primary.get("tags"), list) and primary["tags"]:
        entry["last_mechanism_id"] = primary["tags"][0]

    entry_path = domains / f"{link_id}.json"
    entry_path.write_text(json.dumps(entry, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # lite knowledge mirror
    (knowledge / f"{link_id}.json").write_text(
        json.dumps(
            {
                "schema": KNOWLEDGE_SCHEMA,
                "repository": full,
                "lite_facts": list(dossier.lite_facts),
                "signals": list(dossier.signals),
                "updated_at": _utc_now(),
                "receipt_sha256": receipt_sha256,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    # registry index
    index_path = registry / "index.json"
    if index_path.is_file():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            index = {"schema": "glaciereq.library-of-links.index.v1", "links": {}}
    else:
        index = {"schema": "glaciereq.library-of-links.index.v1", "links": {}}
    links = index.setdefault("links", {})
    links[link_id] = {
        "url": url,
        "domain": "genius",
        "path": f"domains/genius/{link_id}.json",
        "updated_at": entry["updated_at"],
        "tags": entry["tags"][:12],
    }
    index["count"] = len(links)
    index["updated_at"] = _utc_now()
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # README skeleton if missing
    readme = root / "README.md"
    if not readme.is_file():
        readme.write_text(
            "# Library of Links\n\n"
            "Organized lite knowledge and link registry for GlacierEQ.\n\n"
            "- `registry/index.json` — master index\n"
            "- `domains/genius/` — Genius Engine research links\n"
            "- `knowledge/lite/` — accumulated lite facts per leaf\n\n"
            "Updated automatically by Job-App Helix Genius Engine research phase.\n",
            encoding="utf-8",
        )
    return entry_path
