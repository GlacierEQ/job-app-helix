# OFFICIAL_SKILLS — legal hire platform manifest

Schema: `glaciereq.job-app-helix.official-skills.v1`  
HX-28 · 2026-11-17

## Repositories

```json
{
  "public": "GlacierEQ/job-app-helix",
  "private_overlay": "GlacierEQ/job_app_helix",
  "operator_vault": "GlacierEQ/mega-skills",
  "private_overlay_merge": {
    "pr": "https://github.com/GlacierEQ/job_app_helix/pull/1",
    "merge_commit": "895fa867c6ef9ba9c93ea602dcdf1190cab8e6a2"
  }
}
```

## Invariants

```json
{
  "sent_state_requires_external_receipt": true,
  "allow_public_evidence_promotion": false,
  "no_mass_unattended_apply": true
}
```

## Upstream skills

| skill_id | install_ref | upstream_sha | license | public_text |
| --- | --- | --- | --- | --- |
| career-ops | `career-ops-hq/career-ops` | `8831748b952bbe96752b7f0319d46c66069fc544` | MIT | pointer only |
| claude-legal-skill | `evolsb/claude-legal-skill` | `bca0d2e9d5ec81298ddfbfde78fa4f38fb4589b0` | MIT | pointer only |
| legal-redline-tools | `evolsb/legal-redline-tools` | `1dbc70ddfdf594fc4699c31b9077d15e74be56a0` | MIT | pointer only |
| lawve-catalog | `lawve-ai/awesome-legal-skills` | `f9f28cdccbeb98bbdde010042ea9f525ca427c72` | CC BY-NC-ND catalog; skills AGPL | pointer only |
| mcp-eu-compliance | `matematicsolutions/mcp-eu-compliance` | (track at install) | MIT | connector doc in private overlay |
| legalbench | `HazyResearch/legalbench` | (per run receipt) | per-task | scores in `benchmarks/` |

### Five official lawve picks (private vend)

| skill_id | upstream_folder | upstream_sha |
| --- | --- | --- |
| lawve-irac | `irac-prompt-builder-stephane-boghossian` | `f9f28cdccbeb98bbdde010042ea9f525ca427c72` |
| lawve-tech-contract | `tech-contract-review-parth-desai` | `f9f28cdccbeb98bbdde010042ea9f525ca427c72` |
| lawve-eu-ai-act | `eu-ai-act-tanaji-hemant-naik` | `f9f28cdccbeb98bbdde010042ea9f525ca427c72` |
| lawve-expertise-to-skill | `law-expertise-to-skill-adrian-lerer` | `f9f28cdccbeb98bbdde010042ea9f525ca427c72` |
| lawve-privacy-generator | `privacy-policy-generator-malik-taiar` | `f9f28cdccbeb98bbdde010042ea9f525ca427c72` |

Private local paths: `job_app_helix/skills/legal/{irac-prompt-builder,tech-contract-review,eu-ai-act,law-expertise-to-skill,privacy-policy-generator}/`  
Vault mirror index: `mega-skills/legal/INDEX.md`

## Helix composites (private only)

| skill_id | overlay_path |
| --- | --- |
| helix-legal-ops-apply | `skills/hire/helix-legal-ops-apply/SKILL.md` |
| helix-contract-demo | `skills/legal/helix-contract-demo/SKILL.md` |
| helix-compliance-talk-track | `skills/legal/helix-compliance-talk-track/SKILL.md` |

## npx skills one-liners

```bash
npx skills add career-ops-hq/career-ops -a cursor
npx skills add evolsb/claude-legal-skill -a cursor
npx skills add lawve-ai/awesome-legal-skills --skill irac-prompt-builder-stephane-boghossian -a cursor
npx skills add lawve-ai/awesome-legal-skills --skill tech-contract-review-parth-desai -a cursor
npx skills add lawve-ai/awesome-legal-skills --skill eu-ai-act-tanaji-hemant-naik -a cursor
npx skills add lawve-ai/awesome-legal-skills --skill law-expertise-to-skill-adrian-lerer -a cursor
npx skills add lawve-ai/awesome-legal-skills --skill privacy-policy-generator-malik-taiar -a cursor
```

## Benchmark subset (official)

Tasks: `hearsay`, `rule_qa`, `definition_extraction`, `privacy_policy_entailment`, `contract_nli`  
Placeholder: `benchmarks/legalbench-subset.placeholder.json`
