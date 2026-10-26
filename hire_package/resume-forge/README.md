# resume-forge

ATS-safe, human-grade document renderer for the job hunt: resumes, cover letters,
and whatever packet documents come next. Content in `content/`, design in `theme.py`,
artifacts in `out/`.

## Why it exists

Recruiters read resumes; parsers scrape them. Most "pretty" resumes break the
scrape (text boxes, tables, graphics, multi-column). Most ATS-safe resumes look
like a tax form. The forge does both:

- **Scrapes:** single column, no text boxes / images / layout tables, standard
  fonts (Calibri), real heading text, chronological order, standard section
  names. Every glyph the parser reads is a glyph the human reads.
- **Shines:** glacier-teal identity, letter-spaced small-cap section heads with
  hairline rules, right-aligned dates via tab stops, hanging-indent bullets,
  proof numbers set **bold** inline.

## Variants

| variant    | content file        | output                                        |
|------------|---------------------|-----------------------------------------------|
| `master`   | `content/master.yaml`   | `out/Casey_Barton_Resume_Master.{docx,pdf}`   |
| `scale-fde`| `content/scale-fde.yaml`| `out/Casey_Barton_Resume_ScaleAI.{docx,pdf}`  |
| `databricks-fde` | `content/databricks-fde.yaml` | `out/Casey_Barton_Resume_Databricks_FDE.{docx,pdf}` |
| `scale-fde-ps` | `content/scale-fde-ps.yaml` | `out/Casey_Barton_Resume_Scale_FDE_PublicSector.{docx,pdf}` |
| `clickup-maf-senior` | `content/clickup-maf-senior.yaml` | `out/Casey_Barton_Resume_ClickUp_MAF_Senior.{docx,pdf}` |
| `harvey-agents-staff` | `content/harvey-agents-staff.yaml` | `out/Casey_Barton_Resume_Harvey_Agents_Staff.{docx,pdf}` |

New lane? Copy a content YAML, retune the profile + bullet order for the role,
run the forge. The engine doesn't change.

## Cover letters

```bash
python3 cover.py --letter scale-ai-fde --pdf
```

Letters live in `content/cover/*.yaml` and share the candidate truth in
`content/_candidate.yaml`. The engine **fails closed**: any `**bold**` number
in a letter that isn't in the candidate's `kit_numbers` allowlist raises
`HonestyError` instead of rendering. Add a number to the allowlist only with
his approval.

## Usage

```bash
python3 forge.py --variant master --pdf
python3 forge.py --variant scale-fde --pdf
```

Requires: `python-docx`, `pyyaml`, LibreOffice (`soffice`) for PDF.

## Content rules (standing)

- Kit numbers only (95/95, 989-test, 65 MCP, 1,413-repo). No clearance claims
  beyond eligibility. No customer logos. No production-at-their-company claims.
- Every claim must already be true in the repo. The forge styles; it never
  invents.
- Inline `**bold**` markup in YAML strings renders as bold runs (for metrics).
- 2-page target. If a variant spills to 3, cut words, not design.
