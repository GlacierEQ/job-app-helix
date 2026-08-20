"""Acquire attributable company intelligence from explicit source plans.

The acquisition layer closes the gap between source discovery and the existing
company-intelligence refresh/fit/application pipeline. It deliberately does not
"summarize the web" with an opaque model. Every emitted signal is extracted from
an operator-specified source, constrained to approved domains, content-addressed,
and accompanied by a deterministic acquisition receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .company_intelligence import CompanyIntelligence, CompanySignal, load_company_intelligence
from .company_intelligence_refresh import persist_refresh, refresh_company_intelligence

ExtractorKind = Literal["html", "json", "text"]
_MAX_SOURCE_BYTES = 2_000_000
_DEFAULT_TIMEOUT_SECONDS = 15.0


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _reference_domain(value: str) -> str:
    return value.strip().lower().rstrip(".")


def _domain_allowed(hostname: str, allowed_domains: Sequence[str]) -> bool:
    host = _reference_domain(hostname)
    return any(
        host == domain or host.endswith(f".{domain}")
        for domain in (_reference_domain(item) for item in allowed_domains)
        if domain
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_json(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SourceSpec:
    kind: str
    source_url: str
    allowed_domains: tuple[str, ...]
    include_patterns: tuple[str, ...]
    extractor: ExtractorKind = "html"
    exclude_patterns: tuple[str, ...] = ()
    json_paths: tuple[str, ...] = ()
    source_title: str = ""
    max_statements: int = 4

    def __post_init__(self) -> None:
        parsed = urlparse(self.source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("source_url must be an absolute HTTP(S) URL")
        if not self.allowed_domains:
            raise ValueError("allowed_domains must not be empty")
        if not _domain_allowed(parsed.hostname, self.allowed_domains):
            raise ValueError("source_url hostname is outside allowed_domains")
        if not self.include_patterns:
            raise ValueError("include_patterns must not be empty")
        if self.max_statements <= 0:
            raise ValueError("max_statements must be positive")
        for pattern in (*self.include_patterns, *self.exclude_patterns):
            re.compile(pattern)
        if self.extractor == "json" and not self.json_paths:
            raise ValueError("json sources require at least one json_path")


@dataclass(frozen=True)
class AcquisitionPlan:
    schema: str
    company_id: str
    company: str
    max_age_days: int
    sources: tuple[SourceSpec, ...]

    def __post_init__(self) -> None:
        if not self.company_id.strip() or not self.company.strip():
            raise ValueError("company_id and company must not be empty")
        if self.max_age_days <= 0:
            raise ValueError("max_age_days must be positive")
        if not self.sources:
            raise ValueError("acquisition plan requires at least one source")


@dataclass(frozen=True)
class FetchedSource:
    requested_url: str
    final_url: str
    status: int
    content_type: str
    body: bytes
    fetched_at: str
    etag: str = ""
    last_modified: str = ""


@dataclass(frozen=True)
class SourceReceipt:
    requested_url: str
    final_url: str
    kind: str
    status: int
    content_type: str
    content_sha256: str
    fetched_at: str
    etag: str
    last_modified: str
    extracted_statement_count: int
    extracted_statement_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AcquisitionResult:
    intelligence: CompanyIntelligence
    sources: tuple[SourceReceipt, ...]
    receipt_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "glaciereq.company-intelligence-acquisition.v1",
            "company_id": self.intelligence.company_id,
            "company": self.intelligence.company,
            "collected_at": self.intelligence.collected_at,
            "signal_count": len(self.intelligence.signals),
            "sources": [source.to_dict() for source in self.sources],
            "receipt_sha256": self.receipt_sha256,
        }


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._blocked_depth = 0
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag.lower() in {"script", "style", "noscript", "template", "svg"}:
            self._blocked_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "template", "svg"}:
            self._blocked_depth = max(0, self._blocked_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._blocked_depth == 0 and data.strip():
            self._chunks.append(data.strip())

    def text(self) -> str:
        return " ".join(self._chunks)


def _decode_body(source: FetchedSource) -> str:
    content_type = source.content_type.lower()
    charset = "utf-8"
    match = re.search(r"charset=([\w.-]+)", content_type)
    if match:
        charset = match.group(1)
    try:
        return source.body.decode(charset)
    except (LookupError, UnicodeDecodeError):
        return source.body.decode("utf-8", errors="replace")


def _extract_json_path(payload: Any, path: str) -> Any:
    current = payload
    for part in (segment for segment in path.strip("/").split("/") if segment):
        if isinstance(current, Mapping):
            if part not in current:
                raise ValueError(f"json_path not found: {path}")
            current = current[part]
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError) as exc:
                raise ValueError(f"invalid list segment in json_path: {path}") from exc
        else:
            raise ValueError(f"json_path traverses a scalar: {path}")
    return current


def _flatten_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        if value.strip():
            yield value.strip()
        return
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _flatten_strings(item)
        return
    if isinstance(value, list):
        for item in value:
            yield from _flatten_strings(item)


def _extract_text(spec: SourceSpec, source: FetchedSource) -> str:
    decoded = _decode_body(source)
    if spec.extractor == "text":
        return decoded
    if spec.extractor == "html":
        parser = _VisibleTextParser()
        parser.feed(decoded)
        return parser.text()

    try:
        payload = json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise ValueError(f"source did not contain valid JSON: {source.final_url}") from exc
    chunks: list[str] = []
    for path in spec.json_paths:
        chunks.extend(_flatten_strings(_extract_json_path(payload, path)))
    return " ".join(chunks)


def _candidate_segments(text: str) -> tuple[str, ...]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return ()
    segments = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])|\s*[\n\r]+\s*", normalized)
    return tuple(segment.strip() for segment in segments if len(segment.strip()) >= 24)


def _extract_statements(spec: SourceSpec, source: FetchedSource) -> tuple[str, ...]:
    include = [re.compile(pattern, re.IGNORECASE) for pattern in spec.include_patterns]
    exclude = [re.compile(pattern, re.IGNORECASE) for pattern in spec.exclude_patterns]
    matches: list[str] = []
    seen: set[str] = set()
    for segment in _candidate_segments(_extract_text(spec, source)):
        if not any(pattern.search(segment) for pattern in include):
            continue
        if any(pattern.search(segment) for pattern in exclude):
            continue
        compact = " ".join(segment.split())
        key = compact.casefold()
        if key in seen:
            continue
        seen.add(key)
        matches.append(compact)
        if len(matches) >= spec.max_statements:
            break
    return tuple(matches)


def fetch_http_source(
    spec: SourceSpec,
    *,
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = _MAX_SOURCE_BYTES,
    now: Callable[[], datetime] = _utc_now,
) -> FetchedSource:
    """Fetch one source while enforcing domain, redirect, size, and protocol boundaries."""
    request = Request(
        spec.source_url,
        headers={
            "Accept": "text/html,application/json,text/plain;q=0.9,*/*;q=0.1",
            "User-Agent": "GlacierEQ-JobAppHelix-Intelligence/1.0",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            final_url = response.geturl()
            final = urlparse(final_url)
            if final.scheme not in {"http", "https"} or not final.hostname:
                raise ValueError("source redirected to a non-HTTP(S) URL")
            if not _domain_allowed(final.hostname, spec.allowed_domains):
                raise ValueError(
                    f"source redirected outside allowed_domains: {spec.source_url} -> {final_url}"
                )
            length_header = response.headers.get("Content-Length")
            if length_header and int(length_header) > max_bytes:
                raise ValueError(f"source exceeds maximum size of {max_bytes} bytes")
            body = response.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise ValueError(f"source exceeds maximum size of {max_bytes} bytes")
            return FetchedSource(
                requested_url=spec.source_url,
                final_url=final_url,
                status=int(response.status),
                content_type=response.headers.get("Content-Type", ""),
                body=body,
                fetched_at=_iso(now()),
                etag=response.headers.get("ETag", ""),
                last_modified=response.headers.get("Last-Modified", ""),
            )
    except HTTPError as exc:
        raise RuntimeError(f"company source HTTP {exc.code}: {spec.source_url}") from exc
    except URLError as exc:
        raise RuntimeError(f"company source fetch failed: {spec.source_url}: {exc.reason}") from exc


Transport = Callable[[SourceSpec], FetchedSource]


def acquire_company_intelligence(
    plan: AcquisitionPlan,
    *,
    transport: Transport = fetch_http_source,
    now: Callable[[], datetime] = _utc_now,
) -> AcquisitionResult:
    """Execute a plan and produce source-addressed company intelligence."""
    clock = now().astimezone(UTC)
    collected_at = _iso(clock)
    signals: list[CompanySignal] = []
    source_receipts: list[SourceReceipt] = []

    for spec in plan.sources:
        source = transport(spec)
        final = urlparse(source.final_url)
        if not final.hostname or not _domain_allowed(final.hostname, spec.allowed_domains):
            raise ValueError(
                "transport returned a source outside allowed_domains: " f"{source.final_url}"
            )
        statements = _extract_statements(spec, source)
        statement_digest = hashlib.sha256("\n".join(statements).encode("utf-8")).hexdigest()
        source_receipts.append(
            SourceReceipt(
                requested_url=source.requested_url,
                final_url=source.final_url,
                kind=spec.kind,
                status=source.status,
                content_type=source.content_type,
                content_sha256=_sha256_bytes(source.body),
                fetched_at=source.fetched_at,
                etag=source.etag,
                last_modified=source.last_modified,
                extracted_statement_count=len(statements),
                extracted_statement_sha256=statement_digest,
            )
        )
        for statement in statements:
            signals.append(
                CompanySignal(
                    kind=spec.kind,
                    statement=statement,
                    source_url=source.final_url,
                    source_title=spec.source_title,
                    observed_at=source.fetched_at,
                )
            )

    if not signals:
        raise ValueError("acquisition produced no attributable company signals")

    signals.sort(key=lambda signal: (signal.kind, signal.source_url, signal.statement))
    intelligence = CompanyIntelligence(
        schema="glaciereq.company-intelligence.v1",
        company_id=plan.company_id,
        company=plan.company,
        collected_at=collected_at,
        max_age_days=plan.max_age_days,
        signals=tuple(signals),
    )
    receipt_base = {
        "schema": "glaciereq.company-intelligence-acquisition.v1",
        "plan_schema": plan.schema,
        "company_id": plan.company_id,
        "company": plan.company,
        "collected_at": collected_at,
        "signals": [asdict(signal) for signal in intelligence.signals],
        "sources": [receipt.to_dict() for receipt in source_receipts],
    }
    return AcquisitionResult(
        intelligence=intelligence,
        sources=tuple(source_receipts),
        receipt_sha256=_sha256_json(receipt_base),
    )


def load_acquisition_plan(path: Path) -> AcquisitionPlan:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError("acquisition plan must be a JSON object")
    raw_sources = payload.get("sources")
    if not isinstance(raw_sources, list):
        raise ValueError("acquisition plan sources must be a list")
    sources = tuple(
        SourceSpec(
            kind=str(item["kind"]),
            source_url=str(item["source_url"]),
            allowed_domains=tuple(str(value) for value in item["allowed_domains"]),
            include_patterns=tuple(str(value) for value in item["include_patterns"]),
            extractor=str(item.get("extractor", "html")),  # type: ignore[arg-type]
            exclude_patterns=tuple(str(value) for value in item.get("exclude_patterns", [])),
            json_paths=tuple(str(value) for value in item.get("json_paths", [])),
            source_title=str(item.get("source_title", "")),
            max_statements=int(item.get("max_statements", 4)),
        )
        for item in raw_sources
    )
    return AcquisitionPlan(
        schema=str(payload.get("schema", "glaciereq.company-intelligence-acquisition-plan.v1")),
        company_id=str(payload["company_id"]),
        company=str(payload["company"]),
        max_age_days=int(payload.get("max_age_days", 45)),
        sources=sources,
    )


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-app-helix-company-acquire",
        description=(
            "Acquire attributable company signals from explicit official-source plans and "
            "optionally feed them directly into the provenance-preserving refresh engine."
        ),
    )
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--incoming", type=Path, required=True)
    parser.add_argument("--acquisition-receipt", type=Path, required=True)
    parser.add_argument("--current", type=Path)
    parser.add_argument("--active", type=Path)
    parser.add_argument("--history", type=Path)
    parser.add_argument("--refresh-receipt", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    plan = load_acquisition_plan(args.plan)
    result = acquire_company_intelligence(plan)
    _write_json(args.incoming, result.intelligence.as_dict())
    _write_json(args.acquisition_receipt, result.to_dict())

    refresh_args = (args.current, args.active, args.history, args.refresh_receipt)
    if any(refresh_args) and not all(refresh_args):
        raise SystemExit(
            "--current, --active, --history, and --refresh-receipt must be supplied together"
        )
    if all(refresh_args):
        current = load_company_intelligence(args.current)
        refresh = refresh_company_intelligence(current, result.intelligence)
        persist_refresh(
            refresh,
            active_path=args.active,
            history_path=args.history,
            receipt_path=args.refresh_receipt,
        )
        print(
            json.dumps(
                {
                    "acquisition_receipt_sha256": result.receipt_sha256,
                    "refresh_receipt_sha256": refresh.receipt.receipt_sha256,
                    "signal_count": len(result.intelligence.signals),
                },
                sort_keys=True,
            )
        )
        return 0

    print(json.dumps(result.to_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
