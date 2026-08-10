# Innovation scaffold batch — 2026-08-10T0924Z

**Count:** 53 company innovation leaves

Each repo is **DISCOVERED scaffold only** with `DEV_UP_INSTRUCTIONS.md` for implementing AIs.

| Company | Repo | Innovation | Bottleneck source |
|---------|------|------------|-------------------|
| AMD | `amd-hetero-placement-contract` | Heterogeneous Placement Contract | atlas_shard |
| Adobe | `adobe-creative-provenance-gate` | Creative Provenance Gate | atlas_shard |
| Anduril | `anduril-sensor-health-quorum` | Sensor Health Quorum | atlas_shard |
| Atlassian | `atlassian-workgraph-intent-twin` | Workgraph Intent Twin | synthesized |
| Baseten | `baseten-serving-slo-circuit` | Serving SLO Circuit | synthesized |
| Blue Origin | `blue-origin-cryo-telemetry-half-life` | Cryo Telemetry Half-Life | atlas_shard |
| Cerebras | `cerebras-wafer-batch-admission-gate` | Wafer Batch Admission Gate | atlas_shard |
| Cloudflare | `cloudflare-edge-cap-mint` | Edge Cap Mint | atlas_shard |
| Cognition | `cognition-execution-checkpoint-lattice` | Execution Checkpoint Lattice | innovation_queue |
| Cohere | `cohere-retrieval-claim-fence` | Retrieval Claim Fence | atlas_shard |
| CoreWeave | `coreweave-rack-power-autopilot` | Rack Power Autopilot | atlas_shard |
| Crusoe | `crusoe-rack-to-token-autopilot` | Rack-to-Token Autopilot | innovation_queue |
| Cursor / Anysphere | `cursor-patch-intent-twin` | Patch Intent Twin | innovation_queue |
| Databricks | `databricks-notebook-claim-fence` | Notebook Claim Fence | atlas_shard |
| Elastic | `elastic-trajectory-index-layout` | Trajectory Index Layout | synthesized |
| Fireworks AI | `fireworks-ai-optimization-safety-envelope` | Optimization Safety Envelope | innovation_queue |
| GitHub | `github-pr-authority-matrix` | PR Authority Matrix | synthesized |
| GitLab | `gitlab-pipeline-intent-contract` | Pipeline Intent Contract | synthesized |
| Glean | `glean-enterprise-search-claim-fence` | Enterprise Search Claim Fence | synthesized |
| Groq | `groq-jitter-envelope-contract` | Jitter Envelope Contract | atlas_shard |
| Hugging Face | `hugging-face-model-card-provenance-seal` | Model Card Provenance Seal | atlas_shard |
| IBM | `ibm-governed-tool-catalog` | Governed Tool Catalog | atlas_shard |
| Intel | `intel-npu-placement-passport` | NPU Placement Passport | atlas_shard |
| Lambda | `lambda-useful-gpu-minute-contract` | Useful-GPU-Minute Contract | innovation_queue |
| Linear | `linear-issue-intent-twin` | Issue Intent Twin | synthesized |
| Lockheed Martin | `lockheed-martin-mission-assurance-gateway` | Mission Assurance Gateway | synthesized |
| Mistral AI | `mistral-open-weight-eval-fence` | Open Weight Eval Fence | atlas_shard |
| Modal | `modal-ephemeral-sandbox-receipt` | Ephemeral Sandbox Receipt | synthesized |
| MongoDB | `mongodb-operational-semantic-twin-index` | Operational-Semantic Twin Index | innovation_queue |
| MotherDuck | `motherduck-local-cloud-query-passport` | Local-Cloud Query Passport | synthesized |
| NASA | `nasa-command-authority-half-life` | Command Authority Half-Life | atlas_shard |
| Nebius | `nebius-cluster-energy-admission` | Cluster Energy Admission | synthesized |
| Oracle | `oracle-sovereign-data-boundary-gate` | Sovereign Data Boundary Gate | atlas_shard |
| Palantir | `palantir-object-authority-matrix` | Object Authority Matrix | atlas_shard |
| Pinecone | `pinecone-retrieval-outcome-optimizer` | Retrieval Outcome Optimizer | innovation_queue |
| Qdrant | `qdrant-collection-quorum-guard` | Collection Quorum Guard | synthesized |
| Qualcomm | `qualcomm-on-device-budget-futures` | On-Device Budget Futures | atlas_shard |
| Redis | `redis-stream-claim-cursor-fence` | Stream Claim Cursor Fence | synthesized |
| Replicate | `replicate-model-version-pin-gate` | Model Version Pin Gate | synthesized |
| Replit | `replit-workspace-cap-matrix` | Workspace Cap Matrix | synthesized |
| Rocket Lab | `rocket-lab-launch-hold-receipt` | Launch Hold Receipt | atlas_shard |
| Runpod | `runpod-pod-preempt-receipt` | Pod Preempt Receipt | synthesized |
| Salesforce | `salesforce-crm-action-authority` | CRM Action Authority | atlas_shard |
| Scale AI | `scale-ai-label-consensus-fence` | Label Consensus Fence | atlas_shard |
| Snowflake | `snowflake-warehouse-spend-circuit` | Warehouse Spend Circuit | atlas_shard |
| Sourcegraph | `sourcegraph-code-nav-intent-gate` | Code Nav Intent Gate | synthesized |
| Supabase | `supabase-policy-carrying-ai-data-plane` | Policy-Carrying AI Data Plane | innovation_queue |
| Together AI | `together-ai-open-model-fidelity-passport` | Open-Model Fidelity Passport | innovation_queue |
| Vercel | `vercel-deploy-preview-authority` | Deploy Preview Authority | atlas_shard |
| Waymo | `waymo-uncertainty-lane-graph` | Uncertainty Lane Graph | atlas_shard |
| Weaviate | `weaviate-hybrid-search-claim-fence` | Hybrid Search Claim Fence | synthesized |
| Windsurf | `windsurf-cascade-intent-twin` | Cascade Intent Twin | synthesized |
| Zoox | `zoox-fleet-skill-promotion-gate` | Fleet Skill Promotion Gate | atlas_shard |

## How another AI fills code

1. Open `repos/<repo>/DEV_UP_INSTRUCTIONS.md`
2. Implement `src/*.py` mechanism (allow + refuse + digests)
3. Green `pytest` + `scripts/operate.py`
4. Keep non-affiliation; do not PROMOTE with gap-receipt present

