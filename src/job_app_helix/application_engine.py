from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RepositoryProof:
    repository: str
    level: str
    state: str
    visibility: str
    admission: str
    origin: str

    @property
    def recruiter_usable(self) -> bool:
        return (
            self.visibility == "public"
            and self.admission == "HELIX_ADMITTED"
            and self.state in {"PROMOTED", "REFERENCE_ONLY"}
        )


@dataclass(frozen=True)
class CompanyTarget:
    company_id: str
    display_name: str
    track_state: str
    target_roles: tuple[str, ...]
    recruiter_thesis: str
    gap_or_next_gate: str
    non_affiliation: str
    repositories: tuple[RepositoryProof, ...]

    @property
    def recruiter_proofs(self) -> tuple[RepositoryProof, ...]:
        usable = [
            proof
            for proof in self.repositories
            if proof.recruiter_usable
        ]

        def sort_key(item: RepositoryProof) -> tuple[int, str]:
            return _level_rank(item.level), item.repository

        return tuple(
            sorted(
                usable,
                key=sort_key,
                reverse=True,
            )
        )


@dataclass(frozen=True)
class ApplicationKit:
    schema: str
    company_id: str
    company: str
    role: str
    track_state: str
    recruiter_thesis: str
    proof_repositories: tuple[dict[str, str], ...]
    known_gap: str
    non_affiliation: str
    readiness: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _level_rank(level: str) -> int:
    match = re.fullmatch(
        r"L(\d+)",
        str(level).strip().upper(),
    )
    return int(match.group(1)) if match else -1


def _slug(value: str) -> str:
    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        value.casefold(),
    ).strip("-")
    return slug or "target"


def _source_manifest_root() -> Path | None:
    candidate = Path(__file__).resolve().parents[2] / "manifests"
    return candidate if candidate.is_dir() else None


def default_manifest_root() -> Path:
    configured = os.environ.get("JOB_APP_HELIX_MANIFEST_ROOT")
    if configured:
        root = Path(configured).expanduser().resolve()
        if not root.is_dir():
            raise FileNotFoundError(
                "configured manifest root does not exist: "
                f"{root}"
            )
        return root

    source = _source_manifest_root()
    if source is not None:
        return source

    packaged = files("job_app_helix").joinpath("_library_manifests")
    packaged_path = Path(str(packaged))
    if packaged_path.is_dir():
        return packaged_path
    raise FileNotFoundError("job-app-helix manifests are unavailable")


def _repository_proof(
    value: Any,
    *,
    company_id: str,
    index: int,
) -> RepositoryProof:
    if not isinstance(value, list) or len(value) < 6:
        raise ValueError(
            f"{company_id}.repositories[{index}] must contain six fields"
        )
    fields = tuple(str(item) for item in value[:6])
    repository, level, state, visibility, admission, origin = fields
    if "/" not in repository:
        raise ValueError(
            f"{company_id}.repositories[{index}] has invalid repository"
        )
    return RepositoryProof(
        repository,
        level,
        state,
        visibility,
        admission,
        origin,
    )


def _company(value: Mapping[str, Any]) -> CompanyTarget:
    required = (
        "company_id",
        "display_name",
        "track_state",
        "target_roles",
        "recruiter_thesis",
        "gap_or_next_gate",
        "non_affiliation",
        "repositories",
    )
    missing = [
        key
        for key in required
        if key not in value
    ]
    if missing:
        raise ValueError(
            "company dossier missing fields: " + ", ".join(missing)
        )

    company_id = str(value["company_id"])
    raw_roles = value["target_roles"]
    raw_repositories = value["repositories"]
    if not isinstance(raw_roles, list) or not raw_roles:
        raise ValueError(
            f"{company_id}.target_roles must be a non-empty list"
        )
    if not isinstance(raw_repositories, list):
        raise ValueError(
            f"{company_id}.repositories must be a list"
        )

    repositories = tuple(
        _repository_proof(
            row,
            company_id=company_id,
            index=index,
        )
        for index, row in enumerate(raw_repositories)
    )
    return CompanyTarget(
        company_id=company_id,
        display_name=str(value["display_name"]),
        track_state=str(value["track_state"]),
        target_roles=tuple(str(role) for role in raw_roles),
        recruiter_thesis=str(value["recruiter_thesis"]),
        gap_or_next_gate=str(value["gap_or_next_gate"]),
        non_affiliation=str(value["non_affiliation"]),
        repositories=repositories,
    )


def load_targets(
    manifest_root: Path | None = None,
) -> tuple[CompanyTarget, ...]:
    root = manifest_root or default_manifest_root()
    dossier_dir = root / "company_dossiers"
    if not dossier_dir.is_dir():
        raise FileNotFoundError(
            "company dossier directory is unavailable: "
            f"{dossier_dir}"
        )

    targets: list[CompanyTarget] = []
    seen: set[str] = set()
    for path in sorted(dossier_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        companies = payload.get("companies", [])
        if not isinstance(companies, list):
            raise ValueError(
                f"{path.name}: companies must be a list"
            )
        for raw in companies:
            if not isinstance(raw, Mapping):
                raise ValueError(
                    f"{path.name}: company record must be an object"
                )
            target = _company(raw)
            if target.company_id in seen:
                raise ValueError(
                    "duplicate company_id: "
                    f"{target.company_id}"
                )
            seen.add(target.company_id)
            targets.append(target)

    if not targets:
        raise ValueError("no company targets were loaded")
    return tuple(
        sorted(
            targets,
            key=lambda item: item.company_id,
        )
    )


def find_target(
    query: str,
    targets: Iterable[CompanyTarget],
) -> CompanyTarget:
    needle = query.strip().casefold()
    if not needle:
        raise ValueError("company is required")
    targets = tuple(targets)
    exact = [
        target
        for target in targets
        if needle
        in {
            target.company_id.casefold(),
            target.display_name.casefold(),
        }
    ]
    if len(exact) == 1:
        return exact[0]

    partial = [
        target
        for target in targets
        if (
            needle in target.company_id.casefold()
            or needle in target.display_name.casefold()
        )
    ]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        raise ValueError(f"unknown company target: {query}")
    raise ValueError(
        "ambiguous company target: "
        + ", ".join(target.company_id for target in partial)
    )


def resolve_role(
    target: CompanyTarget,
    requested: str | None = None,
) -> str:
    if not requested:
        return target.target_roles[0]

    needle = requested.strip().casefold()
    exact = [
        role
        for role in target.target_roles
        if role.casefold() == needle
    ]
    if exact:
        return exact[0]

    partial = [
        role
        for role in target.target_roles
        if needle in role.casefold()
    ]
    if len(partial) == 1:
        return partial[0]
    available = ", ".join(target.target_roles)
    raise ValueError(
        f"role {requested!r} is not a mapped target role for "
        f"{target.display_name}; available: {available}"
    )


def build_application_kit(
    target: CompanyTarget,
    role: str | None = None,
) -> ApplicationKit:
    selected_role = resolve_role(target, role)
    proofs = target.recruiter_proofs
    readiness = (
        "READY_WITH_PUBLIC_PROOF"
        if proofs
        else "INCOMPLETE_NO_ADMITTED_PUBLIC_PROOF"
    )
    proof_rows = tuple(
        {
            "repository": proof.repository,
            "level": proof.level,
            "state": proof.state,
            "role": "public technical proof",
        }
        for proof in proofs
    )
    return ApplicationKit(
        schema="glaciereq.job-application-kit.v1",
        company_id=target.company_id,
        company=target.display_name,
        role=selected_role,
        track_state=target.track_state,
        recruiter_thesis=target.recruiter_thesis,
        proof_repositories=proof_rows,
        known_gap=target.gap_or_next_gate,
        non_affiliation=target.non_affiliation,
        readiness=readiness,
    )


def render_markdown(kit: ApplicationKit) -> str:
    if kit.proof_repositories:
        proof_lines = "\n".join(
            (
                f"- `{row['repository']}` "
                f"({row['level']}, {row['state']})"
            )
            for row in kit.proof_repositories
        )
    else:
        proof_lines = (
            "- No admitted public proof repository is currently available."
        )

    sections = [
        f"# {kit.company} — {kit.role}",
        (
            f"**Readiness:** `{kit.readiness}`  \n"
            f"**Track state:** `{kit.track_state}`"
        ),
        "## Application thesis",
        kit.recruiter_thesis,
        "## Public technical proof",
        proof_lines,
        "## Known gap before claiming more",
        kit.known_gap,
        "## Truth boundary",
        kit.non_affiliation,
        "## Use",
        (
            "This kit is an evidence-bound application brief. It is ready "
            "for role-specific resume, outreach, and cover-letter projection "
            "only to the extent supported by the proof repositories above."
        ),
    ]
    return "\n\n".join(sections).rstrip() + "\n"


def write_application_kit(
    kit: ApplicationKit,
    output_dir: Path,
) -> tuple[Path, Path]:
    target_dir = output_dir / (
        f"{_slug(kit.company_id)}--{_slug(kit.role)}"
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    json_path = target_dir / "application-kit.json"
    markdown_path = target_dir / "APPLICATION_BRIEF.md"
    json_path.write_text(
        json.dumps(
            kit.as_dict(),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_markdown(kit),
        encoding="utf-8",
    )
    return json_path, markdown_path
