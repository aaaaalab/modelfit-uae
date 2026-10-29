# ModelFit

A working English-language competition prototype for UAE Hackathon 2026, Rising Stars: TDRA Challenge 11, Theme 3, Responsible AI & Smart Cognitive Government.

**Demonstration only. No government endorsement, accreditation, production-readiness or authentic government authorization is claimed.** Three fictional candidates, named fictional reviewer personas, simulated model outputs, and configurable service requirements are deliberately labelled. The official TDRA dataset is real and attributed; it does not establish policy obligations.

## Run the three-minute demonstration

See [the presenter script](docs/DEMO_SCRIPT.md). Open the deployed app, use the service-owner persona to review the use case, compare candidates, switch to evaluator, inspect and justify reuse of E2, confirm the six-case simulation, submit, switch to approver, record approval, then simulate model version 1.1 in Monitoring. Six performance-dependent checks reopen; the public-only configuration finding remains applicable. The old decision and its evidence snapshot remain available.

Each browser receives an isolated demo workspace cookie, backed by the database. Refresh preserves progress. Load demo reloads the saved workspace; Reset demo requires confirmation and replaces only that workspace's demo records. Use public or synthetic information only.

## Local setup

Python 3.12+ and Node 22+ are recommended.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cd frontend
corepack enable
pnpm install --frozen-lockfile
pnpm build
cd ..
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Live prototype: https://modelfit-production-04ce.up.railway.app · Source: https://github.com/aaaaalab/modelfit-uae

Visit http://127.0.0.1:8000. The default persistent database is `modelfit.db` (SQLite). Railway uses MySQL through `DATABASE_URL`. For frontend development run `pnpm dev` inside `frontend`; `/api` proxies to the backend on port 8000. API documentation: `/api/docs`. Health: `/api/health`.

```sh
python -m pytest tests -q
```

## Architecture

One Docker deployment serves a compiled React/TypeScript frontend and FastAPI API. SQLAlchemy parameterizes database access. A transactional JSON workspace aggregate in MySQL persists use cases and their versions, model passports, assessment and finding snapshots, evidence, applicability decisions, approvals, conditions, incidents, change events and audit history. Row locking serializes modifications for each workspace; one application worker additionally serializes local SQLite access. This compact prototype schema is intended for a small demonstration, not large-scale analytics. A normalized schema, migrations, tenancy controls and retention procedures are future work.

`backend/rules.py` implements eligibility, thresholds, evidence validity and deterministic change impact. `backend/assistant.py` defines a bounded adapter interface with an explicitly deterministic demonstration implementation. **Optional live evidence summaries are implemented; activation requires a server-side OpenAI key. See [live AI setup](docs/LIVE_AI.md). Without a key, summaries are explicitly simulated.** Summaries cite evidence record IDs, identify uncertainty, and never create evidence or save findings. The live adapter uses source-bound prompting, a timeout, caching and a process-wide request limit; broader adversarial-document testing remains future work. No document instructions are executed and no uploaded content is sent to an AI service.

## Railway deployment

The repository includes `Dockerfile` and `railway.json`. Create the standard Railway MySQL template and a ModelFit application service connected to this repository's `main` branch. Configure:

- `DATABASE_URL=${{MySQL.MYSQL_URL}}` (Railway reference; never copy the resolved password into GitHub).
- `DEMO_MODE=true` (informational demo flag; the app always presents itself as a demo).
- `PORT=8080` if the generated public domain is routed to 8080.

The Docker command uses Railway's `PORT`; health checks use `/api/health`. MySQL passwords remain generated Railway variables. The database uses private networking and a persistent volume. No Redis is used. Source pushes trigger Railway builds. Monitor build and runtime logs, then verify the live health endpoint and the browser journey.

## Rules and limitations

- All applicable mandatory checks must pass with reviewed, unexpired evidence scoped to the exact model and context. A failing mandatory result, unknown/missing evidence, an incomplete follow-up task, or a newer service version blocks approval. Conditional approval cannot bypass these gates.
- Exception-eligible optional issues can be addressed through explicit conditional approval with an owner, deadline and rationale. There is no mandatory-exception bypass or automatic exception approval. All of this is prototype logic awaiting governance validation.
- Editing a service creates a new version, a recorded field-level change event, a new assessment and dependency-driven follow-up checks. Earlier decisions remain historical.
- A model change invalidates model-dependent performance findings. Context-only evidence can be retained only when its dependencies are unchanged. Other material changes route dependent findings to review and create tasks. Changes always produce a fresh assessment; prior decisions remain historical snapshots.
- Eligibility and performance ranking are separate. Only valid eligible candidates can rank by latency, with stable model ID tie-break. The fictional candidates illustrate failure, missing evidence and eventual eligibility. No universal compliance score exists.
- The fixed six-case fixture cannot evaluate a new model version or changed deployment. Attach new public/synthetic evidence, confirm its review, and explicitly record new findings instead.
- The simulator records events; no provider telemetry or production monitoring is connected. Evidence-expiry events conservatively reopen all linked checks. Incidents conservatively reopen model-dependent checks.
- Demo role headers enforce action permissions server-side, but users can select/spoof those roles. They are **not authentication or verified reviewer authority**. Before organizational use: enterprise identity, authorization, separation of duties, tenant security, threat modelling, audit integrity and governance validation are required.
- The server sets security headers, restricts cross-origin mutations, validates request fields and references, limits request bodies to 100 KB, avoids arbitrary URL fetching, and uses safe error responses. Binary uploads are deferred; evidence links and attachment references work. No sensitive personal data should be entered.
- Intake Save progress stores an unfinished form in this browser; Save service version persists the complete validated record server-side. Earlier server versions remain available in exports.
- Review/condition dates default to illustrative future dates and must be checked by the presenter. Accessibility follows practical keyboard, label, contrast, focus, text-direction and reduced-motion measures; no certification is claimed.
- Enterprise SSO, procurement integrations, automatic production telemetry, government-wide federation, large-scale benchmarks and legally validated policy automation are future capabilities.

## Competition materials

- [Data sources and provenance](docs/DATA_PROVENANCE.md)
- [Three-minute demo script](docs/DEMO_SCRIPT.md)
- [Business Model Canvas — hypotheses](docs/BUSINESS_MODEL_CANVAS.md)
- [90-day execution plan](docs/90_DAY_PLAN.md)
- [Impact measurement plan and judging alignment](docs/IMPACT_PLAN.md)
- [Validation record](docs/VALIDATION.md)

The challenge's 80% evaluation-time reduction and 100% compliance ambitions remain targets to validate. ModelFit reports completed checks, mandatory coverage, evidence gaps, justified reuse, timestamps and reopened tasks; it claims no validated savings or legal compliance.
