# Canonical Recruiter Surface Deployment

## Outcome

Job-App Helix publishes one public, evidence-bound recruiter presentation at:

`https://glaciereq.github.io/job-app-helix/`

The website is not a separately maintained marketing project. It is generated from the canonical candidate records under `hire_package/casey-barton/` and deployed only from `main`.

## Source-of-truth path

```text
candidate_node.json
+ evidence_ledger.json
+ application_spiral.json
+ coordinator_candidate_receipt.json
+ recruiter and technical Markdown
                     │
                     ▼
scripts/build_recruiter_site.py
                     │
                     ▼
artifacts/pages-site/
  index.html
  styles.css
  app.js
  public source records
  deployment-manifest.json
                     │
                     ▼
GitHub Pages artifact → github-pages environment
```

## Deployment authority

Pull requests receive build and validation authority only. They cannot deploy.

Only a qualifying `main` event receives:

- `pages: write`;
- `id-token: write`;
- access to the `github-pages` environment.

The deployment uses GitHub's official Pages actions:

- `actions/configure-pages@v5`;
- `actions/upload-pages-artifact@v4`;
- `actions/deploy-pages@v4`.

## Evidence contract

Every build must prove:

1. the candidate, evidence ledger, and spiral JSON parse successfully;
2. timestamps are timezone-aware;
3. primary roles have presentation routes;
4. relationship values use the compiled Helix enum;
5. AKOS remains `VERIFIED_TEST` with immutable source evidence;
6. the coordinator remains `CANDIDATE_TEST_PROOF` until its hosted promotion completes;
7. APEX activation remains `BLOCKED` while bridge credentials are absent;
8. every local link resolves inside the Pages artifact;
9. direct phone and email details are absent from public files;
10. every deployed payload is SHA-256 listed in `deployment-manifest.json`.

## Failure behavior

- An unresolved template marker fails the build.
- A broken local link fails the build.
- A symbolic link or unexpected file type fails the build.
- Evidence-state drift fails the test suite.
- A failed build produces no deployment.
- A pull request cannot publish.
- A Pages configuration or deployment failure remains visible as a failed workflow rather than being converted into a successful documentation result.

## Local build

```bash
python scripts/build_recruiter_site.py \
  --output artifacts/pages-site \
  --source-commit "$(git rev-parse HEAD)"

python -m pytest -q tests/test_recruiter_site_deployment.py
```

Serve the generated site locally with:

```bash
python -m http.server 8000 --directory artifacts/pages-site
```

## Canonical limitations

Publishing the candidate surface proves that this static presentation was deployed from a specific Helix commit. It does not prove portfolio-wide production deployment, customer impact, scale, performance, or the hosted state of independently governed repositories.
