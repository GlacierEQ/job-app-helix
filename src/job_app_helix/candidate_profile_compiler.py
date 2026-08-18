"""Compile evidence-bound Helix CandidateProfile JSON from Markdown resumes.

The compiler only promotes text already present in resume sources, preserves source hashes,
rejects conflicting identity/contact evidence, and emits a profile consumable by the existing
``load_candidate_profile`` contract without inventing claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .application_operations import load_candidate_profile


class CandidateProfileCompileError(ValueError):
    """Raised when resume evidence cannot be compiled without ambiguity."""


@dataclass(frozen=True)
class ResumeEvidence:
    path: Path
    sha256: str
    name: str
    headline: str
    summary: str
    contact: dict[str, str]
    skills: tuple[str, ...]
    experience: tuple[str, ...]
    achievements: tuple[str, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        value = re.sub(r"\s+", " ", raw).strip()
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return tuple(result)


def _section(lines: Sequence[str], heading: str) -> list[str]:
    wanted = heading.casefold()
    start: int | None = None
    for index, line in enumerate(lines):
        if line.startswith("## ") and line[3:].strip().casefold() == wanted:
            start = index + 1
            break
    if start is None:
        return []
    result: list[str] = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        result.append(line)
    return result


def _parse_identity(lines: Sequence[str], path: Path) -> tuple[str, str]:
    title = next((line[2:].strip() for line in lines if line.startswith("# ")), "")
    if not title:
        raise CandidateProfileCompileError(f"{path} requires a level-1 resume title")
    parts = re.split("\\s+[\\u2014\\u2013-]\\s+", title, maxsplit=1)
    name = parts[0].strip()
    headline = parts[1].strip() if len(parts) == 2 else ""
    if not name:
        raise CandidateProfileCompileError(f"{path} has an empty candidate name")
    return name, headline


def _parse_contact(lines: Sequence[str]) -> dict[str, str]:
    contact: dict[str, str] = {}
    pattern = re.compile(r"\*\*(?P<key>[^*]+)\*\*:\s*(?P<value>[^|]+)")
    for line in lines[:12]:
        for match in pattern.finditer(line):
            key = match.group("key").strip().casefold().replace(" ", "_")
            value = match.group("value").strip()
            if key and value:
                contact[key] = value
    return contact


def _parse_summary(lines: Sequence[str]) -> str:
    body = _section(lines, "Summary")
    paragraphs = [line.strip() for line in body if line.strip() and not line.startswith("---")]
    return " ".join(paragraphs)


def _parse_table_values(lines: Sequence[str]) -> tuple[str, ...]:
    values: list[str] = []
    for line in lines:
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip().strip("*") for cell in line.strip().strip("|").split("|")]
        if len(cells) < 2 or all(set(cell) <= {"-", ":"} for cell in cells if cell):
            continue
        if cells[0].casefold() in {"domain", "category"}:
            continue
        for cell in cells[1:]:
            values.extend(part.strip() for part in cell.split(",") if part.strip())
    return _dedupe(values)


def _parse_projects(lines: Sequence[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    body = _section(lines, "Key Projects")
    experience: list[str] = []
    achievements: list[str] = []
    project = ""
    for line in body:
        stripped = line.strip()
        if stripped.startswith("### "):
            project = stripped[4:].strip()
            continue
        if stripped.startswith("- "):
            claim = stripped[2:].strip()
            evidence = f"{project}: {claim}" if project else claim
            experience.append(evidence)
            if re.search(r"\d", claim):
                achievements.append(evidence)
    return _dedupe(experience), _dedupe(achievements)


def parse_resume(path: Path) -> ResumeEvidence:
    path = path.resolve()
    if not path.is_file():
        raise CandidateProfileCompileError(f"resume not found: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    name, headline = _parse_identity(lines, path)
    experience, achievements = _parse_projects(lines)
    skills = _dedupe(
        (
            *_parse_table_values(_section(lines, "Core Competencies")),
            *_parse_table_values(_section(lines, "Technical Skills")),
        )
    )
    summary = _parse_summary(lines)
    if not summary:
        raise CandidateProfileCompileError(f"{path} requires a Summary section")
    if not skills:
        raise CandidateProfileCompileError(f"{path} contains no structured skills")
    if not experience:
        raise CandidateProfileCompileError(f"{path} contains no Key Projects evidence")
    return ResumeEvidence(
        path=path,
        sha256=_sha256(path),
        name=name,
        headline=headline,
        summary=summary,
        contact=_parse_contact(lines),
        skills=skills,
        experience=experience,
        achievements=achievements,
    )


def _merge_contact(sources: Sequence[ResumeEvidence]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for source in sources:
        for key, value in source.contact.items():
            existing = merged.get(key)
            if existing and existing.casefold() != value.casefold():
                raise CandidateProfileCompileError(
                    f"conflicting contact evidence for {key}: {existing!r} vs {value!r}"
                )
            merged[key] = value
    return merged


def compile_candidate_profile(
    resume_paths: Sequence[Path],
    *,
    profile_id: str | None = None,
) -> dict[str, object]:
    if not resume_paths:
        raise CandidateProfileCompileError("at least one resume source is required")
    sources = tuple(parse_resume(path) for path in resume_paths)
    names = {source.name.casefold(): source.name for source in sources}
    if len(names) != 1:
        raise CandidateProfileCompileError(
            "resume sources disagree on candidate identity: " + ", ".join(names.values())
        )
    primary = sources[0]
    return {
        "schema": "glaciereq.candidate-profile-source.v1",
        "profile_id": profile_id or f"candidate-{primary.name.casefold().replace(' ', '-')}",
        "name": primary.name,
        "headline": primary.headline,
        "summary": primary.summary,
        "skills": list(_dedupe(skill for source in sources for skill in source.skills)),
        "experience": list(_dedupe(item for source in sources for item in source.experience)),
        "achievements": list(
            _dedupe(item for source in sources for item in source.achievements)
        ),
        "contact": _merge_contact(sources),
        "provenance": {
            "policy": "source_text_only_no_claim_invention",
            "sources": [
                {"path": str(source.path), "sha256": source.sha256} for source in sources
            ],
        },
    }


def write_candidate_profile(
    resume_paths: Sequence[Path],
    output_path: Path,
    *,
    profile_id: str | None = None,
) -> dict[str, object]:
    payload = compile_candidate_profile(resume_paths, profile_id=profile_id)
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(output_path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output_path)
    loaded = load_candidate_profile(output_path)
    if loaded.name != payload["name"]:
        raise CandidateProfileCompileError("written profile failed Helix identity validation")
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="job-app-helix-profile")
    parser.add_argument("--resume", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile-id")
    args = parser.parse_args(argv)
    payload = write_candidate_profile(args.resume, args.output, profile_id=args.profile_id)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
