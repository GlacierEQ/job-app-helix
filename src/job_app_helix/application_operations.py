from __future__ import annotations

import hashlib
import html
import json
import re
import sqlite3
import urllib.request
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from .application_engine import ApplicationKit, CompanyTarget, build_application_kit

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "their",
    "this",
    "to",
    "we",
    "with",
    "you",
    "your",
    "will",
    "role",
    "team",
    "work",
    "using",
    "years",
    "experience",
}

TERMINAL_STATUSES = {"OFFER", "REJECTED", "WITHDRAWN", "CLOSED"}
VALID_STATUSES = {
    "DRAFT",
    "READY",
    "QUEUED",
    "SUBMITTED",
    "INTERVIEW",
    "OFFER",
    "REJECTED",
    "WITHDRAWN",
    "CLOSED",
}
ALLOWED_TRANSITIONS = {
    "DRAFT": {"READY", "WITHDRAWN"},
    "READY": {"QUEUED", "SUBMITTED", "WITHDRAWN"},
    "QUEUED": {"SUBMITTED", "WITHDRAWN"},
    "SUBMITTED": {"INTERVIEW", "OFFER", "REJECTED", "WITHDRAWN", "CLOSED"},
    "INTERVIEW": {"INTERVIEW", "OFFER", "REJECTED", "WITHDRAWN", "CLOSED"},
    "OFFER": {"CLOSED"},
    "REJECTED": {"CLOSED"},
    "WITHDRAWN": {"CLOSED"},
    "CLOSED": set(),
}


def _utc_now() -> str:
    value = datetime.now(UTC).replace(microsecond=0)
    return value.isoformat().replace("+00:00", "Z")


def _reference_digest(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _tokens(value: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9+#.-]{1,}", value.casefold())
    return {token for token in tokens if token not in STOPWORDS and len(token) > 1}


def _clean_html(value: str) -> str:
    text = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        value,
        flags=re.I | re.S,
    )
    text = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        text,
        flags=re.I | re.S,
    )
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        parts = re.split(r"[\n;]+", value)
        return tuple(part.strip() for part in parts if part.strip())
    if not isinstance(value, (list, tuple)):
        raise ValueError("expected string or list of strings")
    return tuple(str(item).strip() for item in value if str(item).strip())


def _location_text(value: Any) -> str:
    if not isinstance(value, Mapping):
        return str(value or "").strip()
    address = value.get("address") or value
    if not isinstance(address, Mapping):
        return str(address).strip()
    keys = ("addressLocality", "addressRegion", "addressCountry")
    return ", ".join(
        str(address.get(key)).strip() for key in keys if address.get(key)
    )


@dataclass(frozen=True)
class JobOpening:
    opening_id: str
    company: str
    title: str
    description: str
    location: str
    source: str
    source_url: str | None
    requirements: tuple[str, ...] = ()
    preferred: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    digest: str = ""

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["metadata"] = dict(self.metadata)
        return value


@dataclass(frozen=True)
class CandidateProfile:
    profile_id: str
    name: str
    headline: str
    summary: str
    skills: tuple[str, ...]
    experience: tuple[str, ...]
    achievements: tuple[str, ...]
    contact: Mapping[str, str] = field(default_factory=dict)
    source_digest: str = ""

    def evidence_text(self) -> str:
        values = (
            self.headline,
            self.summary,
            *self.skills,
            *self.experience,
            *self.achievements,
        )
        return " ".join(values)


@dataclass(frozen=True)
class MatchResult:
    opening_id: str
    company_id: str
    mapped_role: str
    overall_score: float
    role_score: float
    skill_score: float
    proof_score: float
    matched_terms: tuple[str, ...]
    missing_terms: tuple[str, ...]
    recommendation: str
    digest: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Projection:
    application_id: str
    opening_id: str
    company_id: str
    role: str
    resume_markdown: str
    cover_letter_markdown: str
    outreach_markdown: str
    claim_sources: tuple[str, ...]
    digest: str


class ApplicationAdapter(Protocol):
    name: str

    def prepare(
        self,
        packet: Mapping[str, Any],
        output_dir: Path,
    ) -> Mapping[str, Any]: ...


class ManualApplicationAdapter:
    """Create a complete human-submittable packet without claiming submission."""

    name = "manual"

    def prepare(
        self,
        packet: Mapping[str, Any],
        output_dir: Path,
    ) -> Mapping[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "SUBMISSION_PACKET.json"
        body = {
            "schema": "glaciereq.manual-application-adapter.v1",
            "adapter": self.name,
            "status": "READY_FOR_MANUAL_SUBMISSION",
            "submission_performed": False,
            "packet": dict(packet),
        }
        path.write_text(
            json.dumps(body, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {
            "adapter": self.name,
            "status": body["status"],
            "submission_performed": False,
            "artifact": str(path),
        }


class JsonApiApplicationAdapter:
    """Generic JSON POST adapter with explicit submission authority."""

    name = "json-api"

    def __init__(
        self,
        endpoint: str,
        *,
        headers: Mapping[str, str] | None = None,
        timeout: float = 20.0,
    ):
        if not endpoint.startswith(("https://", "http://")):
            raise ValueError("application endpoint must be http(s)")
        self.endpoint = endpoint
        self.headers = dict(headers or {})
        self.timeout = timeout

    def _body(self, packet: Mapping[str, Any]) -> bytes:
        return json.dumps(dict(packet), sort_keys=True).encode("utf-8")

    def prepare(
        self,
        packet: Mapping[str, Any],
        output_dir: Path,
    ) -> Mapping[str, Any]:
        output_dir.mkdir(parents=True, exist_ok=True)
        request_body = self._body(packet)
        path = output_dir / "JSON_API_REQUEST.json"
        path.write_bytes(request_body + b"\n")
        return {
            "adapter": self.name,
            "status": "READY",
            "endpoint": self.endpoint,
            "request_digest": hashlib.sha256(request_body).hexdigest(),
            "artifact": str(path),
        }

    def submit(
        self,
        packet: Mapping[str, Any],
        *,
        submit: bool = False,
    ) -> Mapping[str, Any]:
        body = self._body(packet)
        digest = hashlib.sha256(body).hexdigest()
        if not submit:
            return {
                "adapter": self.name,
                "status": "DRY_RUN",
                "submission_performed": False,
                "request_digest": digest,
            }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self.headers,
        }
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            response_body = response.read()
            return {
                "adapter": self.name,
                "status": "SUBMITTED" if 200 <= response.status < 300 else "FAILED",
                "submission_performed": True,
                "http_status": response.status,
                "request_digest": digest,
                "response_digest": hashlib.sha256(response_body).hexdigest(),
                "response_excerpt": response_body[:1000].decode(
                    "utf-8",
                    errors="replace",
                ),
            }


def ingest_job_opening(
    value: Mapping[str, Any],
    *,
    source: str = "record",
    source_url: str | None = None,
) -> JobOpening:
    raw_org = value.get("hiringOrganization")
    org_name = raw_org.get("name") if isinstance(raw_org, Mapping) else raw_org
    company = str(value.get("company") or org_name or "").strip()
    title = str(value.get("title") or "").strip()
    description = _clean_html(str(value.get("description") or ""))
    if not company or not title or not description:
        raise ValueError("job opening requires company, title, and description")

    location = _location_text(value.get("location") or value.get("jobLocation"))
    requirements = _strings(value.get("requirements") or value.get("qualifications"))
    preferred = _strings(
        value.get("preferred") or value.get("preferredQualifications")
    )
    reference = {
        "company": company,
        "title": title,
        "description": description,
        "location": location,
        "source": source,
        "source_url": source_url,
        "requirements": requirements,
        "preferred": preferred,
    }
    digest = _reference_digest(reference)
    opening_id = str(
        value.get("opening_id") or value.get("id") or f"job-{digest[:16]}"
    )
    raw_metadata = value.get("metadata")
    metadata = dict(raw_metadata) if isinstance(raw_metadata, Mapping) else {}
    return JobOpening(
        opening_id=opening_id,
        company=company,
        title=title,
        description=description,
        location=location,
        source=source,
        source_url=source_url,
        requirements=requirements,
        preferred=preferred,
        metadata=metadata,
        digest=digest,
    )


def _find_job_posting(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        if value.get("@type") == "JobPosting":
            return value
        for child in value.values():
            found = _find_job_posting(child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_job_posting(child)
            if found is not None:
                return found
    return None


def ingest_job_opening_url(
    url: str,
    *,
    timeout: float = 20.0,
) -> JobOpening:
    if not url.startswith(("https://", "http://")):
        raise ValueError("job URL must be http(s)")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "job-app-helix/0.3"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        body = response.read().decode(charset, errors="replace")
        content_type = response.headers.get_content_type()

    posting: Mapping[str, Any] | None = None
    looks_json = body.lstrip().startswith(("{", "["))
    if content_type in {"application/json", "application/ld+json"} or looks_json:
        payload = json.loads(body)
        posting = _find_job_posting(payload)
        if posting is None and isinstance(payload, Mapping):
            posting = payload
    else:
        pattern = (
            r"<script[^>]+type=[\"']application/ld\+json[\"']"
            r"[^>]*>(.*?)</script>"
        )
        for match in re.finditer(pattern, body, flags=re.I | re.S):
            try:
                payload = json.loads(html.unescape(match.group(1)))
            except json.JSONDecodeError:
                continue
            posting = _find_job_posting(payload)
            if posting is not None:
                break

    if posting is None:
        raise ValueError("no JobPosting payload found at URL")
    organization = posting.get("hiringOrganization")
    company = (
        organization.get("name") if isinstance(organization, Mapping) else organization
    )
    normalized = dict(posting)
    normalized["company"] = company or posting.get("company")
    return ingest_job_opening(normalized, source="url", source_url=url)


def load_job_opening(path: Path) -> JobOpening:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("job opening file must contain an object")
    return ingest_job_opening(payload, source="file", source_url=str(path))


def load_candidate_profile(path: Path) -> CandidateProfile:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError("candidate profile must contain an object")
    name = str(value.get("name") or "").strip()
    if not name:
        raise ValueError("candidate profile requires name")
    raw_contact = value.get("contact")
    body = {
        "name": name,
        "headline": str(value.get("headline") or "").strip(),
        "summary": str(value.get("summary") or "").strip(),
        "skills": _strings(value.get("skills")),
        "experience": _strings(value.get("experience")),
        "achievements": _strings(value.get("achievements")),
        "contact": dict(raw_contact) if isinstance(raw_contact, Mapping) else {},
    }
    digest = _reference_digest(body)
    return CandidateProfile(
        profile_id=str(value.get("profile_id") or f"candidate-{digest[:16]}"),
        source_digest=digest,
        **body,
    )


def match_opening(
    opening: JobOpening,
    target: CompanyTarget,
    profile: CandidateProfile,
    *,
    mapped_role: str | None = None,
) -> MatchResult:
    role = mapped_role or target.target_roles[0]
    role_tokens = _tokens(role)
    title_tokens = _tokens(opening.title)
    role_score = len(role_tokens & title_tokens) / max(1, len(role_tokens | title_tokens))

    requirement_text = " ".join(
        (*opening.requirements, *opening.preferred, opening.description)
    )
    requirement_tokens = _tokens(requirement_text)
    profile_tokens = _tokens(profile.evidence_text())
    matched = tuple(sorted(requirement_tokens & profile_tokens))
    missing = tuple(sorted(requirement_tokens - profile_tokens))
    skill_score = len(matched) / max(1, len(requirement_tokens))
    proof_count = len(target.recruiter_proofs)
    proof_score = min(1.0, proof_count / 3.0)
    overall = round(
        (0.35 * role_score) + (0.50 * skill_score) + (0.15 * proof_score),
        6,
    )
    if proof_count == 0:
        recommendation = "BLOCKED_NO_PUBLIC_PROOF"
    elif overall >= 0.55:
        recommendation = "STRONG_MATCH"
    elif overall >= 0.30:
        recommendation = "VIABLE_MATCH"
    else:
        recommendation = "WEAK_MATCH"
    body = {
        "opening_id": opening.opening_id,
        "company_id": target.company_id,
        "mapped_role": role,
        "overall_score": overall,
        "role_score": round(role_score, 6),
        "skill_score": round(skill_score, 6),
        "proof_score": round(proof_score, 6),
        "matched_terms": matched,
        "missing_terms": missing,
        "recommendation": recommendation,
    }
    return MatchResult(digest=_reference_digest(body), **body)


def _resume_markdown(
    opening: JobOpening,
    target: CompanyTarget,
    kit: ApplicationKit,
    profile: CandidateProfile,
) -> str:
    opening_text = opening.description + " " + " ".join(opening.requirements)
    relevant = [
        skill for skill in profile.skills if _tokens(skill) & _tokens(opening_text)
    ] or list(profile.skills[:8])
    experience = "\n".join(f"- {item}" for item in profile.experience)
    achievements = "\n".join(f"- {item}" for item in profile.achievements)
    proof = "\n".join(f"- {row['repository']}" for row in kit.proof_repositories)
    sections = [
        f"# {profile.name}",
        profile.headline,
        "## Target",
        f"{opening.title} — {target.display_name}",
        "## Summary",
        profile.summary,
        "## Relevant skills",
        ", ".join(relevant) or "No skills supplied in candidate profile.",
        "## Evidence-backed experience",
        experience or "- No experience bullets supplied in candidate profile.",
        "## Selected achievements",
        achievements or "- No achievement bullets supplied in candidate profile.",
        "## Public technical proof",
        proof,
        "## Truth boundary",
        kit.non_affiliation,
    ]
    return "\n\n".join(sections).rstrip() + "\n"


def _cover_letter_markdown(
    opening: JobOpening,
    target: CompanyTarget,
    kit: ApplicationKit,
    profile: CandidateProfile,
    match: MatchResult,
) -> str:
    proof = "\n".join(f"- {row['repository']}" for row in kit.proof_repositories)
    recommendation = match.recommendation.replace("_", " ").lower()
    paragraphs = [
        f"# Cover Letter — {target.display_name} / {opening.title}",
        "Dear Hiring Team,",
        f"I am applying for the {opening.title} role. {profile.summary}",
        (
            "My strongest evidence for this application is concrete work rather "
            f"than unsupported claims. {kit.recruiter_thesis}"
        ),
        "Public proof relevant to this application:\n" + proof,
        (
            f"The role is a {recommendation} against the supplied profile and job "
            f"description (match score {match.overall_score:.2f}). I would welcome "
            "the opportunity to discuss the systems and implementation decisions "
            "behind this work."
        ),
        f"Sincerely,\n{profile.name}",
        f"Truth boundary: {kit.non_affiliation}",
    ]
    return "\n\n".join(paragraphs).rstrip() + "\n"


def _outreach_markdown(
    opening: JobOpening,
    target: CompanyTarget,
    kit: ApplicationKit,
    profile: CandidateProfile,
) -> str:
    proof_repos = [row["repository"] for row in kit.proof_repositories]
    summary = profile.headline or profile.summary
    proof = ", ".join(proof_repos[:3])
    paragraphs = [
        f"Subject: {opening.title} — {profile.name}",
        (
            f"I'm applying for {opening.title} at {target.display_name}. My work "
            f"centers on {summary}. The most relevant public proof for this role is "
            f"{proof}. I'd value a conversation about where that evidence maps to "
            "the team's current bottlenecks."
        ),
        kit.non_affiliation,
    ]
    return "\n\n".join(paragraphs).rstrip() + "\n"


def project_application(
    opening: JobOpening,
    target: CompanyTarget,
    profile: CandidateProfile,
    *,
    role: str | None = None,
) -> tuple[ApplicationKit, MatchResult, Projection]:
    kit = build_application_kit(target, role)
    if not kit.proof_repositories:
        raise ValueError("cannot project application without admitted public proof")
    match = match_opening(opening, target, profile, mapped_role=kit.role)
    resume = _resume_markdown(opening, target, kit, profile)
    cover = _cover_letter_markdown(opening, target, kit, profile, match)
    outreach = _outreach_markdown(opening, target, kit, profile)
    proof_repos = [row["repository"] for row in kit.proof_repositories]
    body = {
        "opening": opening.digest,
        "kit": kit.as_dict(),
        "match": match.as_dict(),
        "profile": profile.source_digest,
        "resume": resume,
        "cover": cover,
        "outreach": outreach,
    }
    digest = _reference_digest(body)
    projection = Projection(
        application_id=f"app-{digest[:16]}",
        opening_id=opening.opening_id,
        company_id=target.company_id,
        role=opening.title,
        resume_markdown=resume,
        cover_letter_markdown=cover,
        outreach_markdown=outreach,
        claim_sources=tuple(
            [f"candidate-profile:{profile.source_digest}", *proof_repos]
        ),
        digest=digest,
    )
    return kit, match, projection


def write_projection(
    projection: Projection,
    match: MatchResult,
    output_dir: Path,
) -> Mapping[str, str]:
    target = output_dir / projection.application_id
    target.mkdir(parents=True, exist_ok=True)
    files = {
        "resume": target / "RESUME.md",
        "cover_letter": target / "COVER_LETTER.md",
        "outreach": target / "OUTREACH.md",
        "match": target / "MATCH.json",
        "receipt": target / "PROJECTION_RECEIPT.json",
    }
    files["resume"].write_text(projection.resume_markdown, encoding="utf-8")
    files["cover_letter"].write_text(
        projection.cover_letter_markdown,
        encoding="utf-8",
    )
    files["outreach"].write_text(projection.outreach_markdown, encoding="utf-8")
    files["match"].write_text(
        json.dumps(match.as_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    receipt = {
        "schema": "glaciereq.application-projection-receipt.v1",
        "application_id": projection.application_id,
        "opening_id": projection.opening_id,
        "company_id": projection.company_id,
        "claim_sources": list(projection.claim_sources),
        "projection_digest": projection.digest,
        "status": "READY",
    }
    files["receipt"].write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {key: str(path) for key, path in files.items()}


class ApplicationStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self._init_schema()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> ApplicationStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _init_schema(self) -> None:
        self.connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS openings (
                opening_id TEXT PRIMARY KEY,
                digest TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS applications (
                application_id TEXT PRIMARY KEY,
                opening_id TEXT NOT NULL REFERENCES openings(opening_id),
                company_id TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT NOT NULL,
                packet_dir TEXT,
                receipt_digest TEXT NOT NULL,
                external_reference TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id TEXT NOT NULL REFERENCES applications(application_id),
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                occurred_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_application_status
                ON applications(status);
            CREATE INDEX IF NOT EXISTS idx_events_application
                ON events(application_id, occurred_at);
            """
        )
        self.connection.commit()

    def save_opening(self, opening: JobOpening) -> None:
        payload = json.dumps(opening.as_dict(), sort_keys=True)
        self.connection.execute(
            """
            INSERT INTO openings(opening_id,digest,payload_json,created_at)
            VALUES(?,?,?,?)
            ON CONFLICT(opening_id) DO UPDATE SET
                digest=excluded.digest,
                payload_json=excluded.payload_json
            """,
            (opening.opening_id, opening.digest, payload, _utc_now()),
        )
        self.connection.commit()

    def _event(
        self,
        application_id: str,
        event_type: str,
        payload: Mapping[str, Any],
        occurred_at: str | None = None,
    ) -> None:
        self.connection.execute(
            """
            INSERT INTO events(application_id,event_type,payload_json,occurred_at)
            VALUES(?,?,?,?)
            """,
            (
                application_id,
                event_type,
                json.dumps(dict(payload), sort_keys=True),
                occurred_at or _utc_now(),
            ),
        )

    def create_application(
        self,
        projection: Projection,
        *,
        packet_dir: str | None = None,
    ) -> str:
        now = _utc_now()
        existing = self.connection.execute(
            "SELECT application_id FROM applications WHERE application_id=?",
            (projection.application_id,),
        ).fetchone()
        self.connection.execute(
            """
            INSERT INTO applications(
                application_id,opening_id,company_id,role,status,packet_dir,
                receipt_digest,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(application_id) DO UPDATE SET
                packet_dir=excluded.packet_dir,
                receipt_digest=excluded.receipt_digest,
                updated_at=excluded.updated_at
            """,
            (
                projection.application_id,
                projection.opening_id,
                projection.company_id,
                projection.role,
                "READY",
                packet_dir,
                projection.digest,
                now,
                now,
            ),
        )
        if existing is None:
            self._event(
                projection.application_id,
                "CREATED",
                {"projection_digest": projection.digest},
                now,
            )
        self.connection.commit()
        return projection.application_id

    def get_application(self, application_id: str) -> Mapping[str, Any]:
        row = self.connection.execute(
            "SELECT * FROM applications WHERE application_id=?",
            (application_id,),
        ).fetchone()
        if row is None:
            raise KeyError(application_id)
        return dict(row)

    def list_applications(self) -> list[Mapping[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT * FROM applications
            ORDER BY updated_at DESC, application_id
            """
        )
        return [dict(row) for row in rows]

    def transition(
        self,
        application_id: str,
        status: str,
        *,
        external_reference: str | None = None,
        note: str = "",
    ) -> None:
        status = status.upper()
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid application status: {status}")
        current = self.get_application(application_id)
        allowed = ALLOWED_TRANSITIONS[current["status"]]
        if status not in allowed:
            raise ValueError(
                f"invalid application transition: {current['status']} -> {status}"
            )
        if status == "SUBMITTED" and not external_reference:
            raise ValueError("SUBMITTED requires external_reference")
        now = _utc_now()
        self.connection.execute(
            """
            UPDATE applications
            SET status=?,
                external_reference=COALESCE(?,external_reference),
                updated_at=?
            WHERE application_id=?
            """,
            (status, external_reference, now, application_id),
        )
        self._event(
            application_id,
            "STATUS_CHANGED",
            {
                "from": current["status"],
                "to": status,
                "note": note,
                "external_reference": external_reference,
            },
            now,
        )
        self.connection.commit()

    def record_response(
        self,
        application_id: str,
        kind: str,
        note: str,
        *,
        source_reference: str | None = None,
    ) -> None:
        current = self.get_application(application_id)
        self._event(
            application_id,
            "RESPONSE",
            {
                "kind": kind,
                "note": note,
                "source_reference": source_reference,
            },
        )
        target = {
            "interview": "INTERVIEW",
            "offer": "OFFER",
            "rejection": "REJECTED",
        }.get(kind.casefold())
        self.connection.commit()
        allowed = ALLOWED_TRANSITIONS[current["status"]]
        if (
            target
            and current["status"] not in TERMINAL_STATUSES
            and target in allowed
        ):
            self.transition(application_id, target, note=f"response:{kind}")

    def record_feedback(
        self,
        application_id: str,
        outcome: str,
        note: str,
    ) -> None:
        self.get_application(application_id)
        self._event(
            application_id,
            "FEEDBACK",
            {"outcome": outcome, "note": note},
        )
        self.connection.commit()

    def events(self, application_id: str) -> list[Mapping[str, Any]]:
        self.get_application(application_id)
        rows = self.connection.execute(
            """
            SELECT * FROM events
            WHERE application_id=?
            ORDER BY id
            """,
            (application_id,),
        )
        return [
            {**dict(row), "payload": json.loads(row["payload_json"])} for row in rows
        ]

    def feedback_summary(self) -> Mapping[str, Any]:
        rows = self.connection.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM applications
            GROUP BY status
            ORDER BY status
            """
        ).fetchall()
        response_count = self.connection.execute(
            "SELECT COUNT(*) FROM events WHERE event_type='RESPONSE'"
        ).fetchone()[0]
        feedback_count = self.connection.execute(
            "SELECT COUNT(*) FROM events WHERE event_type='FEEDBACK'"
        ).fetchone()[0]
        return {
            "applications": sum(row["count"] for row in rows),
            "by_status": {row["status"]: row["count"] for row in rows},
            "response_events": response_count,
            "feedback_events": feedback_count,
        }


def compile_application_lifecycle(
    opening: JobOpening,
    target: CompanyTarget,
    profile: CandidateProfile,
    *,
    output_dir: Path,
    store: ApplicationStore,
    role: str | None = None,
    adapter: ApplicationAdapter | None = None,
) -> Mapping[str, Any]:
    store.save_opening(opening)
    kit, match, projection = project_application(
        opening,
        target,
        profile,
        role=role,
    )
    artifacts = write_projection(projection, match, output_dir)
    packet = {
        "schema": "glaciereq.application-packet.v1",
        "application_id": projection.application_id,
        "opening": opening.as_dict(),
        "kit": kit.as_dict(),
        "match": match.as_dict(),
        "projection_receipt": projection.digest,
        "artifacts": artifacts,
    }
    adapter_impl = adapter if adapter is not None else ManualApplicationAdapter()
    adapter_receipt = adapter_impl.prepare(
        packet,
        output_dir / projection.application_id / "submission",
    )
    store.create_application(
        projection,
        packet_dir=str(output_dir / projection.application_id),
    )
    return {
        **packet,
        "adapter_receipt": dict(adapter_receipt),
        "status": "READY",
    }
