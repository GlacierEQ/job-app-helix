# Legacy merge/delete (2026-08-09)

## Deleted (useless)
- `job-application/site-v13`
- `job-application/site-v14`

## Merged into one hire surface
- `site-v15/data/portfolio.json` → helix-bound flagships + unified release
- Runtime `truth-proxy` forbids V15 product brand
- `site-v15` remains **only** because Vercel `outputDirectory` points here (path, not version)

## Dropped from flagships
microcode, nanosphere, coordinator, security, servers, energy

## Kept as useful demos
receipt-router (69 tests in current-proof), cooling (green local tests)

## Authority
job-app-helix flagship_registry + current-proof + live headers
