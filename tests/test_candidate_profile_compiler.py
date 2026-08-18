import json
import pathlib
import tempfile
import unittest

from job_app_helix import application_operations, candidate_profile_compiler


RESUME = """# Casey Barton \u2014 Senior Infrastructure Engineer

**Email**: casey@example.com | **GitHub**: github.com/GlacierEQ | **Location**: Honolulu, HI

## Summary

Infrastructure engineer focused on reliable AI and physical systems.

## Core Competencies

| Domain | Skills |
|--------|--------|
| **AI Systems** | multi-agent orchestration, MCP connectors |
| **DevOps** | Docker, Kubernetes, GitHub Actions |

## Key Projects

### Mastermind AI Orchestration
- 9 specialized agents with task chaining
- Real-time health monitoring and self-healing

### FILEBOSS
- SHA-256 and SHA-512 dual hashing

## Technical Skills

| Category | Technologies |
|----------|--------------|
| Languages | Python, TypeScript, SQL |
| Cloud | AWS, GCP, Vercel |
"""


SECONDARY = """# Casey Barton \u2014 AI Systems Engineer

**Email**: casey@example.com | **GitHub**: github.com/GlacierEQ | **Location**: Honolulu, HI

## Summary

Systems engineer building evidence-backed automation.

## Core Competencies

| Domain | Skills |
|--------|--------|
| **AI Systems** | Python, provenance graphs |

## Key Projects

### Evidence Runtime
- 37 connector routes mapped across 9 power dimensions

## Technical Skills

| Category | Technologies |
|----------|--------------|
| Languages | Python, Rust |
"""


def _write(path: pathlib.Path, content: str) -> pathlib.Path:
    path.write_text(content, encoding="utf-8")
    return path


class CandidateProfileCompilerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self._temporary.name)

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def test_single_resume_is_helix_loadable_and_source_bound(self) -> None:
        resume = _write(self.root / "resume.md", RESUME)
        output = self.root / "profile.json"

        payload = candidate_profile_compiler.write_candidate_profile(
            [resume], output, profile_id="casey-production"
        )
        loaded = application_operations.load_candidate_profile(output)

        self.assertEqual(payload["name"], "Casey Barton")
        self.assertEqual(payload["headline"], "Senior Infrastructure Engineer")
        self.assertEqual(loaded.profile_id, "casey-production")
        self.assertIn("multi-agent orchestration", loaded.skills)
        self.assertIn("Python", loaded.skills)
        self.assertEqual(loaded.contact["email"], "casey@example.com")
        self.assertEqual(loaded.contact["location"], "Honolulu, HI")
        self.assertTrue(
            any(item.startswith("Mastermind AI Orchestration:") for item in loaded.experience)
        )
        self.assertTrue(any("9 specialized agents" in item for item in loaded.achievements))
        provenance = payload["provenance"]
        self.assertIsInstance(provenance, dict)
        self.assertEqual(provenance["policy"], "source_text_only_no_claim_invention")
        self.assertTrue(provenance["sources"][0]["sha256"])

    def test_multi_resume_composition_deduplicates_and_preserves_primary_voice(self) -> None:
        primary = _write(self.root / "general.md", RESUME)
        secondary = _write(self.root / "specialized.md", SECONDARY)

        payload = candidate_profile_compiler.compile_candidate_profile([primary, secondary])

        self.assertEqual(payload["headline"], "Senior Infrastructure Engineer")
        self.assertEqual(
            payload["summary"],
            "Infrastructure engineer focused on reliable AI and physical systems.",
        )
        self.assertEqual(payload["skills"].count("Python"), 1)
        self.assertIn("Rust", payload["skills"])
        self.assertTrue(any("37 connector routes" in item for item in payload["experience"]))
        self.assertEqual(len(payload["provenance"]["sources"]), 2)

    def test_conflicting_contact_evidence_fails_closed(self) -> None:
        primary = _write(self.root / "general.md", RESUME)
        conflicting = _write(
            self.root / "conflicting.md",
            SECONDARY.replace("casey@example.com", "different@example.com"),
        )

        with self.assertRaisesRegex(
            candidate_profile_compiler.CandidateProfileCompileError,
            "conflicting contact evidence",
        ):
            candidate_profile_compiler.compile_candidate_profile([primary, conflicting])

    def test_identity_conflict_fails_closed(self) -> None:
        primary = _write(self.root / "general.md", RESUME)
        conflicting = _write(
            self.root / "conflicting.md",
            SECONDARY.replace("Casey Barton", "Another Person", 1),
        )

        with self.assertRaisesRegex(
            candidate_profile_compiler.CandidateProfileCompileError,
            "disagree on candidate identity",
        ):
            candidate_profile_compiler.compile_candidate_profile([primary, conflicting])

    def test_missing_required_evidence_is_rejected(self) -> None:
        resume = _write(
            self.root / "thin.md",
            "# Casey Barton \u2014 Engineer\n\n## Summary\n\nA real summary.\n",
        )

        with self.assertRaisesRegex(
            candidate_profile_compiler.CandidateProfileCompileError,
            "no structured skills",
        ):
            candidate_profile_compiler.compile_candidate_profile([resume])

    def test_output_contains_no_generated_claim_fields(self) -> None:
        resume = _write(self.root / "resume.md", RESUME)
        rendered = json.dumps(candidate_profile_compiler.compile_candidate_profile([resume]))

        self.assertNotIn("world-class", rendered)
        self.assertNotIn("expert in", rendered)
        self.assertIn("source_text_only_no_claim_invention", rendered)
