# Retired workflows

GitHub Actions only runs workflows in `.github/workflows/`, so the files here are
kept for reference and do not run.

- `crystallization-estate-crawl.yml` (retired 2026-09-30): an hourly crawl of the
  private estate that requires the `GLACIEREQ_ESTATE_TOKEN` secret. This public
  repository does not carry that secret, so every scheduled run failed. Running
  a private-estate crawl from a public repository would also expose its logs
  and artifacts publicly.

- `crystallization-estate-push-smoke.yml` (retired 2026-09-30): the push-time
  smoke test for the same crawl; it also requires `GLACIEREQ_ESTATE_TOKEN` and
  failed on every matching push.

- `pages.yml` "Deploy recruiter presentation" (retired 2026-09-30): the GitHub
  Pages build. Its public-portfolio census fails closed because
  `manifests/portfolio_repositories.json` still lists repositories that are no
  longer public. Dropping them from the census isn't enough, because the
  estate compiler's semantic capability donors and the company dossiers
  reference some of them too, so compilation still fails closed. The live
  recruiter surface is the Vercel site built from `GlacierEQ/job-application`.
  Restore this workflow once those manifests reflect the public set.

To restore one, move it back: `git mv .github/workflows-retired/<name>.yml .github/workflows/`.
