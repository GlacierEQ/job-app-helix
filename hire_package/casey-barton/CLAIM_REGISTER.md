# Claim Register and Tactical Hardening

## Source-bound public surface

- **Only share:** https://casey-barton-glaciereq.vercel.app/
- **Deploy source:** `GlacierEQ/job-application` (`site-v15/`)
- **Control plane:** `GlacierEQ/job-app-helix` (this package + manifests)
- **Do not share:** `glaciereq.github.io/job-app-helix/` (Pages not enabled), `job-application.vercel.app` (wrong project), `glaciereq.com` (unrelated)

## Verified / allowed

- Exact 67-repository Job-App Helix boundary: one control-plane root plus 66 child repositories.
- Live hire site at the reference Vercel URL responds HTTP 200 with security headers (CSP, frame deny, nosniff); product stack is labeled on `/data/portfolio.json` release (not the legacy “V15” product name).
- AKOS 94/94 tests across 12 modules on Python 3.11-3.13.
- Verified 21-node README Mesh rollout.
- Public Actions Runner Host: one live governed APEX Public Action Face path is verified on `main` by successful issue-triggered run `31280194602` at commit `e012d913c4646816d25de831ff642cedb9290a9d`. The run completed ingress authorization, strict envelope validation, OIDC/Keymaster bridge verification, one-repository private control-token minting, private control-plane checks, immutable job claiming, one-repository workload-token minting, catalog-approved private workload checkout, exact repository+commit binding, isolated adapter execution, post-run integrity verification, private result return, sanitized public status publication, and explicit revocation of both runtime tokens. This proves one operational governed execution path; it does not prove every route, workload, lane, scale level, or reliability target.
- B.S. Marine Biology, University of Hawaii at Manoa, 2016.
- Certified Home Inspector, Diamond Head Home Inspections, 2020-2024.

## Candidate / partial

- Agent Coordinator: 62/62 independent Python 3.13 tests; hosted build/wheel/matrix promotion pending.
- Public runner coordinator route: registered; do not generalize the verified APEX Public Action Face path into proof that every coordinator route, workload, or lane is operational.
- Document intelligence: describe architecture and pipeline stages; do not claim unsupported throughput.

## Excluded

- 400,000 agents.
- 1,200 files per hour.
- Production-grade across the complete owned-library census.
- Top-percentile or elite ranking as fact.
- Programming-language mastery by count.
- Federal evidence compliance conclusions.
- AWS Cloud Institute described as a master's degree.
- Unsupported compensation, customer, revenue, latency, scale, or deployment claims.

## Tactical rule

Lead with operator or business value, then the architecture, then the exact receipt. Never lead with repository count or technology lists without explaining what changed for a user or team.
