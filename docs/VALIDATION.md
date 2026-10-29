# Validation record

29 October 2026. These are executed checks, not a security audit or certification.

## Local automated checks

- Python suite: **18 tests passed** using the deployment dependency constraints (Python 3.12, SQLAlchemy 2.0.55).
- Covers mandatory failures overriding performance; missing evidence; conditional-approval gates; trimmed reuse rationale and matching dependencies; frozen assessments; exact-version simulation restrictions; preserved decisions; persistence and workspace isolation; role permissions; reset confirmation; all six simulator trigger types; supplier-claim provenance; evidence expiry; request limits and origin checks; service revisions; withdrawal of reuse applicability; dynamic eligibility/ranking; source workbook checksum and facts; and preserving unresolved tasks across successive changes.
- TypeScript check and Vite production build passed.
- One dependency deprecation warning: Starlette's test client reports its httpx integration as deprecated. It does not fail the suite; migration is a maintenance task.

## GitHub checks

The Verify ModelFit workflow runs backend tests and the frontend build on pushes. The first checked run passed both jobs: https://github.com/aaaaalab/modelfit-uae/actions/runs/40824055316 . Later runs can be inspected in the repository Actions page.

## Live browser verification

Verified on https://modelfit-production-04ce.up.railway.app :

- All five navigation areas; service detail; comparison failure and evidence-gap states.
- Reuse dependency review and rationale; mandatory coverage 67% → 83% → 100%.
- Six-case bilingual simulation, including source-linked counts and correctly directed Arabic examples.
- Submission; named demonstration approval; model version 1.0 → 1.1; six reopened checks; retained configuration finding.
- Page refresh preserves reassessment and historical approval with its original snapshot.
- Guided create flow, required-field blocking, saved intake draft across reload, review summary and server-persisted new service.
- Versioned edit: threshold 0.9 → 0.95 creates service v2, a separate assessment and a field-level change event.
- Evidence attachment by HTTPS reference; pending review; confirmation; manual finding; coverage update.
- Source-linked deterministic assistant summary, visibly labelled as simulated and not new evidence.
- Auditor controls are read only; mutation rules are additionally covered by backend tests.
- Evidence-trail export downloaded and parsed as valid JSON with use cases, assessments, approvals and changes.
- 390 × 844 responsive view: document width and scroll width both 390 pixels, with no page overflow. Desktop layout also inspected. Temporary viewport override was reset.
- Screenshots: `docs/screenshots/change-impact.jpg` and `docs/screenshots/mobile.jpg`.

Railway build and runtime logs were reviewed; successful startup and MySQL-backed health were verified. No API keys were supplied to the frontend or committed. No live AI credentials were available; the assistant is simulated.

No accessibility certification, penetration test, real-model benchmark, production telemetry or validated time saving has been performed. Additional trigger combinations and external-browser/assistive-technology coverage remain future work.
