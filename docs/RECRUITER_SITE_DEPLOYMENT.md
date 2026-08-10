# Canonical Recruiter Surface Deployment

## Outcome

Job-App Helix publishes **one** public, evidence-bound recruiter presentation at:

**https://casey-barton-glaciereq.vercel.app/**

| Surface | Role | Status |
|---------|------|--------|
| `casey-barton-glaciereq.vercel.app` | **Canonical public hire surface** | Live (HTTP 200) |
| Source deploy repo | `GlacierEQ/job-application` → `site-v15/` | Production build root |
| Control-plane authority | `GlacierEQ/job-app-helix` manifests + hire package | Evidence + package SoT |
| `glaciereq.github.io/job-app-helix/` | Historical Pages URL | **Not enabled** — do not share |

Do **not** share `job-application.vercel.app` (unrelated project) or the dead GitHub Pages path.

The website is not a free-floating marketing project. Public HTML is compiled from governed records (hire package, flagship registry, helix projection, proof receipts) and deployed only from the production branch of the deploy repo.

## Source-of-truth path

```text
job-app-helix/
  hire_package/casey-barton/   ← candidate package (resume, claims, machine JSON)
  manifests/*                  ← portfolio / flagship / excellence authority
        │
        ▼ (projection + sync)
job-application/
  site-v15/                    ← production static output
  vercel.json                  ← Vercel project config
        │
        ▼
https://casey-barton-glaciereq.vercel.app/
```

Secondary (CI-only) path inside this repository:

```text
scripts/build_compiled_recruiter_site.py
        │
        ▼
artifacts/pages-site/          ← privacy-verified build artifact
        │
        ▼
GitHub Pages deploy job        ← optional; Pages currently disabled on the repo
```

GitHub Pages may be re-enabled as a **mirror**, never as the primary share link. Until Pages is enabled and returns 200 for the recruiter root, every external package must use the Vercel URL.

## Deployment authority

### Vercel (production)

- Project name / alias: `casey-barton-glaciereq`
- Output directory: `site-v15` in `GlacierEQ/job-application`
- Headers: CSP, HSTS, frame deny, nosniff, referrer policy (see live response headers)
- Only production branch deploys update the canonical alias

### GitHub Pages (optional mirror)

Pull requests receive build and validation authority only. They cannot deploy.

Only a qualifying `main` event may attempt Pages deploy:

- `pages: write`
- `id-token: write`
- access to the `github-pages` environment

If Pages is not enabled and `GLACIEREQ_PAGES_TOKEN` is absent, the workflow builds and privacy-checks the artifact, then records a gate — it does **not** claim a public URL.

## Evidence contract

Every public surface must preserve:

1. candidate, evidence ledger, package mesh, and spiral JSON parse successfully;
2. timestamps are timezone-aware;
3. primary roles have presentation routes;
4. relationship values use the compiled Helix enum;
5. AKOS remains `VERIFIED_TEST` with immutable source evidence until a stronger receipt exists;
6. the coordinator remains `CANDIDATE_TEST_PROOF` until hosted promotion completes;
7. unsupported scale, customer, revenue, and affiliation claims stay forbidden;
8. recruiter metrics and display states derive from evidence ledgers rather than parallel tables;
9. repository proof links are pinned to real commits where claimed;
10. generic email and telephone patterns are absent from public static files unless explicitly authorized on the production site contact path;
11. every deployed payload that claims integrity lists SHA-256 where the deployment contract requires it.

## Failure behavior

- An unresolved template marker fails the build.
- A broken local link fails the build.
- A symbolic link or unexpected file type fails the build.
- An output path that contains or overwrites protected repository sources fails before deletion.
- Evidence-state or presentation-metric drift fails the test suite.
- A failed build produces no deployment.
- A pull request cannot publish production.
- A non-`main` manual run cannot publish production.

## Share-link policy (fail closed)

| Link | Share? |
|------|--------|
| `https://casey-barton-glaciereq.vercel.app/` | **Yes — only public share link** |
| `https://casey-barton-glaciereq.vercel.app/resume/` | Yes |
| `https://casey-barton-glaciereq.vercel.app/master/` | Yes (technical diligence) |
| `https://glaciereq.github.io/job-app-helix/` | **No** (404 / not enabled) |
| `https://job-application.vercel.app/` | **No** (wrong project) |
| `https://glaciereq.com` | **No** (unrelated) |
