# Tasks

## 1. Runner and scheduling

- [x] 1.1 Implement the typed pipeline dispatcher and structured summaries for all/selected pipelines; verify unit tests cover deterministic order and `--only` selection
- [x] 1.2 Add `backend/scripts/run_pipelines.py` argument parsing, JSON output, validation errors, upstream error exit codes, and async client cleanup; verify CLI tests cover valid and invalid invocations
- [x] 1.3 Add the compose scheduler worker and document its bounded interval; verify compose configuration parses and the runner command is present

## 2. Simulation service

- [x] 2.1 Implement fictional-only template selection and `simulate_activity()` with type-safe model construction, UTC timestamps, and unique `SIMULATED` provenance; verify unit tests cover every template activity type and real-competitor rejection
- [x] 2.2 Verify simulation writes through the owned activity repository and preserves source immutability; verify an isolated Mongo integration test covers random fictional selection and distinct reruns

## 3. Documentation and verification

- [x] 3.1 Update `docs/roadmap.md` and the relevant API/data contract notes without adding the future HTTP route; verify the roadmap links the PR and the scheduler/CLI contract is documented
- [ ] 3.2 Run the complete quality gate and OpenSpec checks (`npm run check`, integration tests, `openspec validate --all --strict --no-interactive`, and conflict detection); verify all affected tests pass
