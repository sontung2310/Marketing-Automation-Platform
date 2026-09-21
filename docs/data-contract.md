# Data Contract — Intelligence DB

> Parent: [specs.md](specs.md) · Status: Draft v1. Sections marked **VERIFY** are
> assumptions about existing collections. Roadmap Step 0 checks them against
> the live cluster through the MongoDB MCP and then freezes this document.

---

## 1. Principles

1. **Source collections are read-only.** The PoC never writes to CompetitorScope,
   Data-Crawler-Task (DCT) or Pace collections.
2. **One owned database.** Everything the platform writes lives in its own
   database (`MONGODB_DATABASE`, default `marketing_automation`) on the same
   cluster. This covers normalized intelligence, seed data and app state.
3. **Normalize, don't proxy.** Pipelines copy source records into normalized
   collections. The MCP and API read only the normalized collections, so
   source schema drift is contained in one pipeline module.
4. **Provenance on every record.** Each record carries `source.system`,
   `source.ref_id`, `is_mock` and `is_simulated`.
5. **Idempotent ingestion.** There is a unique index on `(source.system,
   source.ref_id)`, and pipelines upsert.
6. **Tenant-ready.** Every tenant-owned record has `company_id`, even though
   the PoC has one tenant.
7. **Stable, prefixed string IDs.** Agents cite these IDs as evidence:
   `cmp_`, `cpt_`, `act_`, `trd_`, `inf_`, `rec_`, `run_`, `ses_`, `del_`,
   `pac_`. Mongo `_id` holds the prefixed ID.

Two different "MongoDB MCP"s appear in this project. Don't confuse them.

| Name | What it is | Used by |
|---|---|---|
| **MongoDB MCP** (`.mcp.json` → `mongodb`) | Read-only inspection tool for developers and coding agents | Humans and Claude/Codex while building. **Never in the runtime path.** |
| **Marketing Intelligence MCP** (`backend/.../mcp_server`) | The platform's own semantic tools over the normalized collections | The Strategy and Execution agents at runtime |

## 2. Enums

```text
ActivityType   = NEW_BLOG | SOCIAL_POST | EXECUTIVE_POST | NEW_PRODUCT | PRODUCT_REMOVED
               | PRICE_CHANGE | PROMOTION | CAMPAIGN_LAUNCH | PAGE_UPDATE
Channel        = WEBSITE | LINKEDIN | X | INSTAGRAM | FACEBOOK | YOUTUBE | REDDIT | NEWS
SourceSystem   = COMPETITORSCOPE | DCT | PACE | MOCK_SEED | SIMULATED
TrendDirection = RISING | STEADY | FALLING
Priority       = HIGH | MEDIUM | LOW
```

The UI and agents use these enums verbatim, in line with CompetitorScope DS
content rules. `NEW_BLOG`, `NEW_PRODUCT`, `PRODUCT_REMOVED`, `PRICE_CHANGE`
and `PAGE_UPDATE` intentionally match CompetitorScope's `change_type` values.

## 3. Owned collections

### 3.1 `companies`

The tenant's own context. The agents read it through `get_company_context`.

```jsonc
{
  "_id": "cmp_marketing_eye",
  "name": "Marketing Eye",
  "website": "https://www.marketingeye.com.au",
  "industry": "B2B marketing agency",
  "region": "AU",
  "summary": "string",
  "icp": [{ "segment": "string", "pains": ["string"], "goals": ["string"] }],
  "positioning": "string",
  "services": [{ "name": "string", "description": "string", "price_from": 0 }],
  "brand_voice": { "tone": ["string"], "do": ["string"], "dont": ["string"], "sample_copy": ["string"] },
  "channels": ["LINKEDIN", "X", "WEBSITE"],
  "content_pillars": ["string"],
  "is_mock": true,
  "updated_at": "ISODate"
}
```

### 3.2 `competitors`

```jsonc
{
  "_id": "cpt_lyfe_marketing",
  "company_id": "cmp_marketing_eye",
  "name": "Lyfe Marketing",
  "website": "https://www.lyfemarketing.com",
  "is_fictional": false,
  "social": { "LINKEDIN": "url|null", "X": "url|null", "INSTAGRAM": "url|null" },
  "executives": [{ "name": "string", "role": "CEO" }],   // fictional competitors only
  "source": { "system": "COMPETITORSCOPE", "ref_id": "string" },
  "is_mock": false
}
```

### 3.3 `competitor_activities` (the feed)

```jsonc
{
  "_id": "act_01J…",                       // ULID-based, time-sortable
  "company_id": "cmp_marketing_eye",
  "competitor_id": "cpt_lyfe_marketing",
  "competitor_name": "Lyfe Marketing",       // denormalized for feed speed
  "activity_type": "NEW_BLOG",
  "channel": "WEBSITE",
  "title": "7 B2B Content Trends for 2026",  // required; derived if the source has none (see §4.1)
  "summary": "string",                       // mechanical, quoted as-is in the UI
  "narrative_summary": "string|null",        // optional richer text
  "url": "https://…|null",
  "author": { "name": "string", "role": "CEO" } ,          // EXECUTIVE_POST only
  "price": { "before": 2500, "after": 1990, "currency": "AUD" }, // PRICE_CHANGE / PROMOTION only
  "engagement": { "likes": 0, "comments": 0, "shares": 0 },      // social types only
  "content_excerpt": "string|null",          // ≤ 1,200 chars, used by "create similar"
  "topics": ["ai-seo", "content-strategy"],
  "occurred_at": "ISODate",                  // when the competitor did it (best estimate)
  "detected_at": "ISODate",                  // when we detected it; feed sort key
  "source": { "system": "COMPETITORSCOPE", "ref_id": "string" },
  "is_mock": false,
  "is_simulated": false,
  "seen_at": "ISODate|null",
  "ingested_at": "ISODate"
}
```

Indexes:

- `{company_id:1, detected_at:-1}`
- `{company_id:1, activity_type:1, detected_at:-1}`
- `{company_id:1, competitor_id:1, detected_at:-1}`
- unique `{"source.system":1, "source.ref_id":1}`
- text index `{title, summary, narrative_summary, content_excerpt, topics}`

### 3.4 `trends`

```jsonc
{
  "_id": "trd_…",
  "company_id": "cmp_marketing_eye",      // trends are scoped to the tenant's market
  "topic": "AI search optimisation (GEO)",
  "keywords": ["geo", "ai overviews", "llm seo"],
  "channel": "LINKEDIN",
  "window_days": 7,
  "mention_count": 412,
  "momentum_pct": 142.0,                  // change vs previous window
  "direction": "RISING",
  "sentiment": 0.31,                      // −1..1
  "sample_posts": [{ "title": "string", "url": "string", "channel": "LINKEDIN" }],
  "computed_at": "ISODate",
  "source": { "system": "PACE|MOCK_SEED", "ref_id": "string" },
  "is_mock": true
}
```

### 3.5 `influencers`

```jsonc
{
  "_id": "inf_…",
  "company_id": "cmp_marketing_eye",
  "name": "string", "handle": "@string", "channel": "LINKEDIN",
  "profile_url": "string",
  "followers": 48200,
  "engagement_rate": 0.036,
  "topics": ["b2b marketing", "ai"],
  "audience_region": "AU",
  "relevance_score": 0.82,                 // 0..1, from DCT ranking or seed
  "evidence": [{ "title": "string", "url": "string" }],
  "source": { "system": "DCT|MOCK_SEED", "ref_id": "string" },
  "is_mock": false
}
```

### 3.6 App-state collections

| Collection | Purpose | Key fields |
|---|---|---|
| `sessions` | One chat thread in the workspace | `_id ses_`, `company_id`, `created_at`, `last_run_id` |
| `runs` | One agent run | `_id run_`, `session_id`, `agent` (`STRATEGY`/`EXECUTION`), `intent`, `trigger`, `route` (method, reason, confidence), `status` (`RUNNING`/`SUCCEEDED`/`FAILED`/`NEEDS_CLARIFICATION`/`REFUSED`), `events[]` (the SSE log), `tool_calls[]`, `skills_loaded[]`, `output` (structured), `usage`, `error`, `started_at`, `finished_at` |
| `recommendations` | Persisted Strategy recommendations. Used by the Topics tab and the "#2" references. | `_id rec_`, `run_id`, `session_id`, `ordinal` (1-based within the run), recommendation fields from agents-spec §6.2, `status` (`OPEN`/`IN_PROGRESS`/`DONE`) |
| `deliverables` | Execution outputs | `_id del_`, `run_id`, deliverable fields from agents-spec §7.2 |
| `proposed_actions` | Actions awaiting approval, plus their outcome | `_id pac_`, `deliverable_id`, `action_type`, `payload`, `status` (`PROPOSED`/`APPROVED`/`EXECUTED`/`DISCARDED`/`FAILED`), `receipt`, timestamps |

## 4. Source mapping

**VERIFY in Step 0.** The database and collection names below are inferred
from sibling repositories and have not been confirmed on the live cluster.

| Source | Assumed location | Target | Pipeline module |
|---|---|---|---|
| CompetitorScope changes | `competitor_monitoring.changes` (production may be in the "RM Mongo" DB, see specs Q1) | `competitor_activities` | `pipelines/competitor_activity.py` |
| CompetitorScope competitors/targets | `competitor_monitoring.competitors`, `monitoring_targets` | `competitors` + the `competitor_name` join | same |
| DCT influencer candidates | DCT DB `influencer_candidates` (+ `influencer_candidate_evidence`) | `influencers` | `pipelines/influencers.py` |
| Pace AI-enriched articles | Article DB `ai_posts` | `trends` (aggregation) | `pipelines/trends.py` |

### 4.1 CompetitorScope `changes` → `competitor_activities`

| Source field | Target | Rule |
|---|---|---|
| `id` | `source.ref_id` | `source.system = COMPETITORSCOPE` |
| `change_type` | `activity_type` | 1:1 for the five shared enums. Unknown values are skipped and logged. |
| `summary` | `summary` | as-is |
| `narrative_summary` | `narrative_summary` | nullable |
| `detected_url` (fallback: the target URL) | `url` | |
| `detected_at` | `detected_at`, `occurred_at` | |
| — | `title` | For `NEW_BLOG`, the post title parsed from `summary` (pattern `New post: "…"`). Otherwise the first sentence of `summary`, at most 120 characters. |
| `is_simulated` | `is_simulated` | missing → `false` |
| monitoring target → competitor | `competitor_id`, `competitor_name` | Only competitors mapped to Marketing Eye are ingested. Test tenants (Brown Bag, Elevation) are excluded. |

### 4.2 DCT `influencer_candidates` → `influencers`

Map name, handle, platform, followers, engagement and topic fields 1:1 where
they exist. Map DCT's rank or score into `relevance_score` (normalized to
0..1), and evidence-ledger entries into `evidence[]`. The exact field names
are frozen in Step 0.

### 4.3 Pace `ai_posts` → `trends`

This is an aggregation, not a copy. The pipeline groups the last 14 days by
the enriched topic or keyword field, and computes `mention_count` for the last
7 days against the previous 7 days to get `momentum_pct`. It keeps the top 3
posts as `sample_posts`. If there are fewer than 50 posts in the window, it
skips the aggregation and uses the seed.

## 5. Mock seed requirements

Seed files live in `backend/app/pipelines/seed/*.json`.
They are loaded by `backend/scripts/seed_db.py`, and every seeded record is
`is_mock: true`.

| Dataset | Minimum content |
|---|---|
| `companies` | 1 (Marketing Eye), with full brand voice, 4 content pillars, 5 services and 2 ICP segments |
| `competitors` | Lyfe Marketing (real; from CompetitorScope if present, otherwise seeded without mock activities) + **Brightlane Marketing** and **Kestrel Growth Co.** (both `is_fictional: true`, each with a named fictional CEO) |
| `competitor_activities` | ≥ 45 records over the last 30 days. **Every** `ActivityType` has at least 3. Channels cover WEBSITE, LINKEDIN, X and INSTAGRAM. At least 6 records fall in the last 48 h, so the feed looks alive. Mock social, executive, campaign and promotion activity belongs only to the fictional competitors. |
| `trends` | ≥ 16 records across LINKEDIN, X, REDDIT and NEWS, mixing RISING, STEADY and FALLING. At least 4 overlap topically with competitor activity, so cross-evidence reasoning is possible. |
| `influencers` | ≥ 20 across LINKEDIN, X and YOUTUBE, with 60% AU audiences and relevance scores spread across 0.3–0.95 |
| Simulation templates | ≥ 2 templates per `ActivityType`, used by `POST /activities/simulate` (records are `is_simulated: true`, `source.system = SIMULATED`) |

Content rules for the seed:

- Seed text is realistic, specific and dated. No lorem ipsum, and no "Example
  Corp".
- URLs for fictional competitors use the reserved `.example` TLD, for
  example `https://brightlane.example/blog/…`, so they can never resolve to a
  real site.
- Adversarial records (prompt-injection text, defamatory bait) exist **only**
  in the eval fixtures. They are never in the demo seed.

## 6. Eval fixture snapshot

`backend/scripts/snapshot_fixture.py` exports the owned collections into
`backend/evals/fixtures/intelligence_v{N}.json`, together with the eval-only
adversarial records. The eval harness loads the snapshot into a throwaway
database (`marketing_automation_eval_<run>`), either on a local `mongo:7`
container (the default, and the one CI uses) or on the dev cluster. Golden cases reference evidence IDs from a specific fixture version.
Bumping the fixture version requires re-validating the cases' `expected_evidence`.
