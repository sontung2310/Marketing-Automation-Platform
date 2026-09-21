# Marketing Automation Platform — PoC Specification

> Status: Draft v1 · 2026-09-21
> Architecture: [architecture-design.html](architecture-design.html)
> Companion specs:
> [data-contract.md](data-contract.md) ·
> [agents-spec.md](agents-spec.md) ·
> [api-contract.md](api-contract.md) ·
> [ui-spec.md](ui-spec.md) ·
> [evaluation-spec.md](evaluation-spec.md) ·
> [roadmap.md](roadmap.md)

---

## 1. Purpose

The PoC shows a client, in one browser page, that the platform can:

1. **Watch the market.** It surfaces competitor activity, trending topics and
   relevant influencers from an Intelligence DB. Background pipelines fill the
   DB from existing MongoDB sources, plus mock data where no source exists yet.
2. **Decide.** A **Marketing Strategy Agent** answers *"what should we do?"*.
   It recommends topics, competitor responses and influencer plays, and grounds
   every recommendation in evidence it retrieved itself.
3. **Act.** A **Marketing Execution Agent** answers *"do this task for me"*. It
   produces the deliverable (blog, social post, CEO post, email, ad copy,
   response brief) and proposes executable actions. The user approves an
   action and a mock connector "executes" it.

The PoC must answer this question for the client in under five minutes of
demo:

> **"My competitor just did something. What does it mean for me, and can the
> platform do the work for me?"**

## 2. Scope

### In scope

| Area | PoC capability |
|---|---|
| Competitor monitoring | Newest-first activity feed of website changes (real, from CompetitorScope) and social/campaign activity (mock). Live push of new items. A "Simulate a signal" demo trigger. |
| Trends | Trending topics per platform, with momentum and sample posts. Derived from existing article data if it exists, otherwise mock. |
| Influencers | Ranked influencer list per topic/platform, from existing DCT influencer candidates plus mock records. |
| Strategy Agent | Topic recommendations, competitor response plans, "why it matters" analysis, influencer recommendations, trend analysis. |
| Execution Agent | Deliverable drafts and proposed mock actions (schedule post, create CMS draft, add to content calendar, create email draft). |
| Request routing | Feed/insight buttons route deterministically. Free-text chat is routed by a classifier. |
| Marketing skills | A curated, vendored subset of `coreyhaines31/marketingskills`, shared by both agents through per-agent allowlists. |
| UI | **One page.** A three-column workspace with a chat composer, following the CompetitorScope Design System. |
| Evaluation | A golden dataset and eval harness for the Router, Strategy Agent and Execution Agent. |

### Out of scope (PoC)

- Authentication, multi-user and billing. The system has a single tenant
  (**Marketing Eye**), but every record carries `company_id` so multi-tenancy
  can be added later.
- Real posting, emailing or CMS writes. All connectors are mock.
- Building new crawlers. The PoC consumes what CompetitorScope and
  Data-Crawler-Task already write, and seeds the rest.
- Analytics and performance measurement (shown on the architecture as future
  work only).
- Mobile-first design. The page is responsive, but the demo target is a
  1440px laptop.

## 3. Users and demo tenant

| Item | Value |
|---|---|
| Primary user | Marketing manager at the tenant company |
| Demo tenant | **Marketing Eye** (marketingeye.com.au). B2B marketing agency, Australia. |
| Real competitor | **Lyfe Marketing** (lyfemarketing.com), with website changes from CompetitorScope |
| Mock competitors | Two **fictional** agencies defined in the seed (see [data-contract.md §5](data-contract.md#5-mock-seed-requirements)) |

**Rule: no fabricated activity is attributed to a real company.** Mock social
posts, campaigns, promotions and CEO posts belong only to the fictional
competitors. Lyfe Marketing only shows real CompetitorScope records, or
records explicitly flagged `is_simulated` by the demo trigger. Every mock or
simulated record is badged in the UI.

## 4. Architecture summary

This section restates the architecture only as far as the specs need it. The
diagrams in [architecture-design.html](architecture-design.html) are
authoritative.

```text
Browser (React + Vite, one page)
   │  REST + SSE
   ▼
Platform API (FastAPI) ── Request Router ── Session/Run store
   │                          │
   │ feed/insight reads       ├──► Marketing Strategy Agent  ─┐  (OpenAI Agents SDK)
   │ (repositories)           └──► Marketing Execution Agent ─┤
   │                                                          │ MCP (streamable HTTP)
   ▼                                                          ▼
Intelligence DB (MongoDB)  ◄──── read ──── Marketing Intelligence MCP server
   ▲                                              Marketing Skills (vendored SKILL.md)
   │ write (normalize / seed)
Intelligence Pipelines ◄── read-only ── Existing MongoDB sources
   (cron / CLI)                         (CompetitorScope changes, DCT influencers, Pace articles)
```

### Architecture rules

These rules carry over from the architecture doc and are enforced by the
specs.

1. **Two agents.** Strategy answers *what should we do*. Execution answers *do
   this task*. They run independently: neither calls the other. The API
   passes context between them, for example "write recommendation #2".
2. **Pipelines are infrastructure, not agents.** They normalize and seed data.
   They never call an LLM to make decisions. They may call one to enrich data,
   such as trend clustering.
3. **Retrieval is on demand.** Agents are never handed a pre-built data
   bundle. They decide what to query through the Intelligence MCP. The only
   thing injected into a run is the **trigger context**: the item the user
   clicked, or the recommendation they referenced.
4. **Skills teach the work.** Marketing methods live in vendored `SKILL.md`
   files, not in agent prompts.
5. **Mock first.** Anything without a real source is seeded, and flagged
   `is_mock: true`.
6. **Execution can expand later.** Real connectors replace mock ones behind
   the same `ProposedAction` contract, without changing the agents.

### Technology decisions

| Concern | Decision |
|---|---|
| Language (backend) | Python 3.11+ |
| Package/env manager | `uv` |
| API | FastAPI, Pydantic v2, SSE via `sse-starlette` |
| Agents | **OpenAI Agents SDK** (`openai-agents`), with structured outputs (`output_type`) |
| Models | Set by env: `OPENAI_MODEL_AGENT`, `OPENAI_MODEL_ROUTER`, `OPENAI_MODEL_JUDGE`. No model names hard-coded. |
| Intelligence MCP | Official `mcp` Python SDK (FastMCP) over streamable HTTP. Agents connect with `MCPServerStreamableHttp`. |
| Database | Existing MongoDB cluster (URI in `.env`), accessed with the PyMongo async API |
| Frontend | React 18 + Vite + TypeScript + Tailwind CSS v4. The Tailwind theme (`src/styles/theme.css`) holds the CompetitorScope Design System tokens, and its components are rebuilt as Tailwind components. |
| Testing | pytest (backend), Vitest (frontend units), Playwright (one E2E demo script), eval harness (`backend/evals/`, data in `evaluation/`) |
| Quality | ruff (lint + format), mypy (strict on `src`), import-linter, ESLint + Prettier; `npm run check` in CI and husky + lint-staged on commit |
| Deployment (PoC) | `docker-compose`: api, mcp, frontend and pipelines on one host (see architecture §06) |

## 5. Capability overview

Each capability has a stable ID so roadmap steps, OpenSpec changes and eval
cases can reference it.

| ID | Capability | Owner | Detail |
|---|---|---|---|
| CAP-DATA-01 | Normalize CompetitorScope changes into `competitor_activities` | Pipelines | [data-contract.md §4](data-contract.md#4-source-mapping) |
| CAP-DATA-02 | Normalize DCT influencer candidates into `influencers` | Pipelines | data-contract.md §4 |
| CAP-DATA-03 | Build `trends` from article data, or from the seed | Pipelines | data-contract.md §4 |
| CAP-DATA-04 | Mock seed for company context, fictional competitors, social activity, trends and influencers | Pipelines | data-contract.md §5 |
| CAP-DATA-05 | Simulate a signal (demo trigger) | API + Pipelines | api-contract.md |
| CAP-MCP-01 | Intelligence MCP read tools | MCP server | [agents-spec.md §3](agents-spec.md#3-marketing-intelligence-mcp) |
| CAP-SKL-01 | Skill library, loader and per-agent allowlists | Agents | agents-spec.md §4 |
| CAP-RTR-01 | Request routing (deterministic + classifier) | API | agents-spec.md §5 |
| CAP-STR-01 | Topic recommendations | Strategy | agents-spec.md §6 |
| CAP-STR-02 | Competitor response plan | Strategy | agents-spec.md §6 |
| CAP-STR-03 | "Why it matters" analysis of one activity | Strategy | agents-spec.md §6 |
| CAP-STR-04 | Influencer recommendations | Strategy | agents-spec.md §6 |
| CAP-STR-05 | Trend analysis | Strategy | agents-spec.md §6 |
| CAP-EXE-01 | "Create similar" deliverable from a competitor activity | Execution | agents-spec.md §7 |
| CAP-EXE-02 | Deliverable from a recommendation | Execution | agents-spec.md §7 |
| CAP-EXE-03 | Free-form deliverable from chat | Execution | agents-spec.md §7 |
| CAP-EXE-04 | Quality and policy check | Execution | agents-spec.md §7 |
| CAP-EXE-05 | Proposed actions, approval and mock execution | Execution + API | agents-spec.md §8 |
| CAP-UI-01 | Competitor activity feed with live updates | UI | [ui-spec.md](ui-spec.md) |
| CAP-UI-02 | Agent workspace and chat composer | UI | ui-spec.md |
| CAP-UI-03 | Insights rail (Trends / Influencers / Topics) | UI | ui-spec.md |
| CAP-EVAL-01..03 | Golden datasets and harness for Router, Strategy and Execution | Evals | [evaluation-spec.md](evaluation-spec.md) |

## 6. Feed actions (type-mapped routing)

Every feed item has one **primary** button, chosen by its `activity_type`.
Items whose primary action goes to Execution also have a secondary **"Why it
matters"** action, which goes to Strategy.

| `activity_type` | Example | Primary button | Agent | Intent | Secondary |
|---|---|---|---|---|---|
| `NEW_BLOG` | Lyfe Marketing published "7 B2B Content Trends for 2026" | **Create a similar blog** | Execution | `CREATE_SIMILAR` → `BLOG_DRAFT` | Why it matters |
| `SOCIAL_POST` | Brightlane posted a LinkedIn carousel on AI SEO | **Create a similar post** (same channel) | Execution | `CREATE_SIMILAR` → `LINKEDIN_POST` / `X_POST` / `INSTAGRAM_POST` | Why it matters |
| `EXECUTIVE_POST` | Brightlane's CEO posted about agency pricing | **Draft a CEO post** | Execution | `CREATE_SIMILAR` → `CEO_POST` | Why it matters |
| `NEW_PRODUCT` | Competitor launched a "Fractional CMO" package | **Plan a response** | Strategy | `RESPONSE_PLAN` | — |
| `PRODUCT_REMOVED` | Competitor removed its SEO starter package | **Plan a response** | Strategy | `RESPONSE_PLAN` | — |
| `PRICE_CHANGE` | Package price `$2,500 → $1,990` | **Plan a response** | Strategy | `RESPONSE_PLAN` | — |
| `PROMOTION` | 20% off annual retainers until 31 Oct | **Plan a response** | Strategy | `RESPONSE_PLAN` | — |
| `CAMPAIGN_LAUNCH` | New "Grow with AI" webinar series | **Plan a response** | Strategy | `RESPONSE_PLAN` | — |
| `PAGE_UPDATE` | Services page rewritten around AI | **Plan a response** | Strategy | `RESPONSE_PLAN` | — |

Response plans end with recommendations. Each recommendation carries a
`next_action`, and the UI renders it as a **"Do this"** button that sends the
recommendation to Execution. This closes the loop from strategy to execution
in two clicks.

**"Create similar" means inspired-by, never copied.** The Execution Agent
must produce original content in Marketing Eye's voice. The policy check in
[agents-spec.md §7.3](agents-spec.md#73-quality-and-policy-check) enforces
this.

## 7. End-to-end demo story (acceptance narrative)

The PoC is done when this script runs live against the seeded environment
without manual intervention. It is also the Playwright E2E test (roadmap Step
8).

1. **Open the page.** The feed shows Marketing Eye's competitor activity,
   newest first, with type badges, titles, links and relative times. The
   Trends tab lists rising topics. The page header shows the last sync time.
2. **A new signal arrives.** The presenter clicks **🎭 Simulate a signal** and
   chooses `EXECUTIVE_POST`. Within 3 seconds a new card appears at the top of
   the feed with a `NEW` marker and a 🧪 SIMULATED badge.
3. **Why it matters.** The presenter clicks *Why it matters*. The Strategy
   Agent streams its progress ("Loading company context", "Searching
   competitor activity", "Loading skill: content-strategy"). It then returns
   2–3 implications, each citing evidence chips that link to feed items and
   trends.
4. **Create the response.** The presenter clicks **Draft a CEO post** on the
   same card. The Execution Agent returns an original LinkedIn post in Marketing
   Eye's voice, a quality-check panel and a proposed action
   `schedule_social_post` (LinkedIn, next Tuesday 09:00 AEST).
5. **Approve.** The presenter approves the action. Its status moves from
   `PROPOSED` to `EXECUTED (mock)`, and the action log shows the mock
   connector's receipt.
6. **Plan a response.** On a `PRICE_CHANGE` card, the presenter clicks **Plan
   a response**. Strategy returns a prioritized response plan. The presenter
   clicks **Do this** on recommendation #2, and Execution drafts the
   deliverable.
7. **Chat.** The presenter types *"What should we post about next week?"* The
   router picks Strategy, which returns topic recommendations; they also
   appear in the Topics tab. The presenter then types *"Write the LinkedIn
   post for recommendation #2"*. The router picks Execution and resolves the
   reference.
8. **Influencers.** In the Influencers tab, the presenter clicks **Draft
   outreach** on an influencer. Execution returns an outreach email draft and
   a `create_email_draft` action.

## 8. Non-functional requirements

| Area | Requirement (PoC) |
|---|---|
| Latency | Feed loads in under 1 s (p95, seeded DB). The first agent progress event arrives within 2 s of the click. A full Strategy run takes 45 s or less (p95), and a full Execution run 60 s or less (p95). |
| Streaming | Every run streams progress steps over SSE. No run goes more than 10 s without a UI update. |
| Grounding | Every Strategy recommendation cites at least one `evidence_id` that exists in the Intelligence DB. Evidence IDs are never invented (checked in evals). |
| Safety | No verbatim copying of competitor content: no run of 12 or more consecutive words copied from the source. No defamatory claims about named competitors. Prompt injection inside ingested content is ignored. No real external side effects. |
| Transparency | Mock and simulated data are always badged. Agent output lists assumptions and data gaps. |
| Observability | Every run persists: route decision, tool calls (name, arguments, duration), skills loaded, final output, token usage and errors. OpenAI Agents SDK tracing is enabled in dev. |
| Config | All secrets and model names come from `.env` through `pydantic-settings`. `.env.example` is committed, `.env` is never committed. |
| Reproducibility | Evals run against a frozen fixture DB, never the live cluster. |
| Cost guard | Maximum of 12 tool calls and 3 skill loads per agent run. A run that hits the limit ends gracefully, with a partial result and a data-gap note. |

## 9. Success criteria (PoC level)

The PoC is accepted when **all** of the following hold. Per-step criteria are
in [roadmap.md](roadmap.md).

1. The demo story in §7 passes as an automated Playwright run three times in a
   row against the seeded environment.
2. Golden-dataset results meet the thresholds in
   [evaluation-spec.md §6](evaluation-spec.md#6-pass-thresholds) for Router,
   Strategy and Execution.
3. Every `activity_type` in §6 has at least one seeded feed item, and its
   button produces a valid output.
4. There are zero safety-category failures in the golden dataset
   (plagiarism, defamation, injection, unethical requests).
5. A reviewer who didn't build the UI finds no violations of the
   design-system checklist in [ui-spec.md §8](ui-spec.md#8-anti-slop-checklist).

## 10. Open questions

| # | Question | Default if unanswered |
|---|---|---|
| Q1 | **Resolved (2026-09-22):** the cluster reachable from this repository exposes only `admin`, `competitors_monitoring_test`, `influencer_discovery`, `local` and `pace_database`; no “RM Mongo” database is present. The available CompetitorScope source is therefore the test database `competitors_monitoring_test.changes`, joined through `monitoring_targets` and `competitors`, not production data. | Use the verified §4.1 mapping as the durable starting point. If production is on another cluster, re-verify its field names, join path, counts and date ranges before Step 1 pipelines are trusted there. |
| Q2 | **Resolved:** yes. The PoC may create and own `MONGODB_DATABASE` (default `marketing_automation`) on the existing cluster for normalized intelligence and app state. | Source collections remain read-only for the life of the PoC. |
| Q3 | **Resolved (2026-09-22):** `pace_database.ai_posts` exists with 37 documents, but 0 are in the preceding 14 days (and the collection is below the 50-post threshold). | Trends are fully seeded (`is_mock: true`) until Pace meets the aggregation threshold. |
| Q4 | Brand-voice source for Marketing Eye | Seeded `companies` document written from the public website; the client can edit it later |
