# Scale AI — Mission Software Engineer, Public Sector (Honolulu) · Outreach Packet

**Candidate:** Casey Del Carpio Barton / GlacierEQ
**Role:** Mission Software Engineer, Public Sector — Honolulu
**Target:** Portal first, then Public Sector Engineering Lead on LinkedIn (lead not yet identified).
**Channel:** Portal application first, then LinkedIn DM
**Campaign state:** OUTREACH_VERIFIED_NOT_SENT
**Send order:** 4 of 4 — only after the req is confirmed open (confirmed open 2026-10-02: fresh mirrors list Honolulu, $138–219k)
**Recorded:** 2026-10-02

## Outreach note (paste-ready, verbatim)

```text
Applied for Mission Software Engineer, Public Sector — Honolulu.

I am already in Honolulu. Three years building a constrained, evidence-grade agent control plane for state and federal work: inspectable state transitions, bounded tool actions, approval gates, recoverable runs. 62/62 on the coordinator. 961-test control plane. 65 MCP connectors, fail-closed authz.

Customer-facing is the other half. I have spent years turning hard system behavior into a decision a non-technical client can use the same day.

No active clearance. Eligible to be sponsored for one. Open to the travel. Not relocating off-island. https://casey-barton-glaciereq.vercel.app/

Casey del Carpio Barton
glacier.equilibrium@gmail.com
```

## Verification receipt

- Req confirmed OPEN 2026-10-02 (mirrors crawled <2 days list Honolulu; $138,000–$219,420 Honolulu band).
- Posting requires "active TS/SCI **or the ability to obtain**" — the note states "No active clearance. Eligible to be sponsored for one." plainly.
- Posting notes >50% travel; the note states openness to travel, no off-island relocation.
- 90-day waiting period policy on reapplications — on record.
- Numbers from the application kit: 62/62, 961-test control plane, 65 MCP connectors, fail-closed authz.

## Gating

Send only after req confirmed open (satisfied 2026-10-02) and only if willing to say "no clearance" (stated in the note).

## Asana tracking
- Outreach board: "Job Outreach — Oct 2026" (https://app.asana.com/1/1211490156667710/project/1219120163374486)
- Task GID: 1219120253448281 (subtasks: apply / DM with verbatim note / log-send; dependencies enforce send order)
- Replies land in "Interview Pipeline" (https://app.asana.com/1/1211490156667710/project/1219142018872587)

## 2026-10-04 — portal application initiated, verification pending
- Greenhouse sent a security code for the Scale AI application (2026-10-04 20:12 HST, to glacier.equilibrium@gmail.com): "Copy and paste this code into the security code field on your application... After you enter the code, resubmit your application."
- State: portal application STARTED but not completed — the code must be entered and the application resubmitted. The emailed code is 2 days old and likely expired; expect to request a fresh code on re-entry.
- (Found 2026-10-06 during the post-reauthorization sweep of the dark window.)

## 2026-10-06 — target posting switched (his call)
- The original "Mission Software Engineer, Public Sector" ($138–219k) posting is no longer on Scale's Greenhouse board. Per his decision, the target is now "Forward Deployed Software Engineer, Public Sector" — Honolulu.
- The Senior Mission posting ($223–279k) requires active TS/SCI; not pursued.
- Resume Casey_Barton_Resume_ScaleAI.docx (FDE-angled) and the portal-submit flow carry over; cover letter text updated to the Forward Deployed title.

## 2026-10-06 — resume rebuilt through resume-forge (his call)
- He asked for stronger, better-looking resumes that still scrape clean. Built `hire_package/resume-forge/`: python-docx engine, ATS-safe theme (single column, standard fonts, no layout tables), glacier-teal design, 2-page target. Content from YAML; `**bold**` inline for proof numbers.
- `Casey_Barton_Resume_ScaleAI.docx` / `.pdf` in this folder REPLACED with the forged FDE variant (verified: 2 pages, all kit numbers, section order intact, no markup leak). Upload this version, not the old plain one.
- Master variant: `hire_package/resume-forge/out/Casey_Barton_Resume_Master.{docx,pdf}` — canonical base for future lanes.
- 2026-10-07: Education section added to both variants (B.S. UH Manoa 2016; AWS Cloud Institute Cloud Computing 2024; CSU undergraduate coursework). Application-folder copies refreshed.

## 2026-10-13 — cover letter forged (his call)
- Built the cover-letter foundation: `hire_package/resume-forge/cover.py` + `content/_candidate.yaml` (shared truth) + `theme.py` (design system extracted from forge.py; resume output verified byte-identical).
- Honesty gate: the engine FAILS CLOSED — any **bold** number not in the candidate's kit_numbers allowlist raises HonestyError instead of rendering.
- `Cover_Letter_ScaleAI_FDE.{docx,pdf}` in this folder — 1 page, matches the resume identity, kit numbers only, no clearance claims beyond eligibility.

## 2026-10-13 — numbers upgraded to live-verified (his call: "Those numbers are SHIT")
- Kit refreshed: 1,313 → **1,395** repos (GraphQL census today), 961 → **989** test functions (fresh clone today), apex-control-plane **988** test fns (+91 in 6 days). 62/62 still exact.
- All 6 resume variants + cover letter rebuilt with new numbers; this folder's resume + letter refreshed.
- Honesty gate proved itself: caught a stale **961** the bulk edit missed and refused to render until fixed.
