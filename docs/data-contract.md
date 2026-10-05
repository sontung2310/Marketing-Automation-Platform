# Data Contract — Intelligence DB

> Parent: [specs.md](specs.md) · Status: Draft v1. Roadmap Step 0 verified the
> source mappings in §4 against the reachable test cluster, not production,
> through the read-only MongoDB MCP on 2026-09-22.

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
| **MongoDB MCP** (`.mcp.json` → `mongodb`) | Read-only inspection tool for developers and coding agents | Humans and coding agents while building. **Never in the runtime path.** |
| **Marketing Intelligence MCP** (`backend/.../mcp_server`) | The platform's own semantic tools over the normalized collections | The Strategy and Execution agents at runtime |

Step 2 adds only this read-only runtime boundary. It introduces no collection,
stored field, migration or data-contract schema change; it reads the existing
typed repository models and serializes their public `id` fields for agents.

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
  "tracked_keywords": ["Marketing Strategy", "Digital Marketing Trends", "AI in Marketing", "Marketing Automation", "Social Media Marketing"],
  "content_pillars": ["string"],
  "spokesperson": { "name": "string", "role": "string", "voice_notes": ["string"] },
  "is_mock": true,
  "updated_at": "ISODate"
}
```

`tracked_keywords` configures social listening. It contains 1–20 non-empty
terms, each trimmed and unique case-insensitively; validation preserves the
first trimmed spelling. The seed uses `Marketing Strategy`, `Digital Marketing
Trends`, `AI in Marketing`, `Marketing Automation` and `Social Media
Marketing`. These terms scope the Trends
and Influencers panels only; they never filter the competitor activity feed.

`spokesperson` is required: whose first-person voice a `CEO_POST` uses, with
`voice_notes` holding the tone rules (at least one). The seed uses a fictional
founder, Morgan Hale (Founder and CEO), never a real person.

### 3.2 `competitors`

```jsonc
{
  "_id": "cpt_<source ObjectId>",
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
  "competitor_id": "cpt_<source ObjectId>",
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

Indexes:

- `{company_id:1, momentum_pct:-1}`
- unique `{"source.system":1, "source.ref_id":1}`
- text index `{topic, keywords}`

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

Indexes:

- `{company_id:1, relevance_score:-1}`
- unique `{"source.system":1, "source.ref_id":1}`
- text index `{name, topics}`

### 3.6 App-state collections

| Collection | Purpose | Key fields |
|---|---|---|
| `sessions` | One chat thread in the workspace | `_id ses_`, `company_id`, `created_at`, `last_run_id` |
| `runs` | One agent run | `_id run_`, `session_id`, `agent` (`STRATEGY`/`EXECUTION`), `intent`, `trigger`, `route` (method, reason, confidence), `status` (`RUNNING`/`SUCCEEDED`/`FAILED`/`NEEDS_CLARIFICATION`/`REFUSED`), `events[]` (the SSE log), `tool_calls[]`, `skills_loaded[]`, `output` (structured), `usage`, `error`, `started_at`, `finished_at` |
| `recommendations` | Persisted Strategy recommendations. Used by the Strategy panel and the "#2" references. | `_id rec_`, `run_id`, `session_id`, `ordinal` (1-based within the run), recommendation fields from agents-spec §6.2, `status` (`OPEN`/`IN_PROGRESS`/`DONE`/`SUPERSEDED`; a later successful Strategy run in the same session supersedes the older `OPEN` set). `run_label` is not stored: the API derives it from the run's `intent` and `trigger` when serving `GET /recommendations`. |
| `deliverables` | Execution outputs | `_id del_`, `run_id`, deliverable fields from agents-spec §7.2, including `image_suggestions[]` (`placement`, `content`, `style`; empty when the type takes none) |
| `proposed_actions` | Actions awaiting approval, plus their outcome | `_id pac_`, `deliverable_id`, `action_type`, `summary`, `payload` (built in code, agents-spec §8), `status` (`PROPOSED`/`APPROVED`/`EXECUTED`/`DISCARDED`/`FAILED`), `receipt` (mock: `mock: true`), `error` (why a `FAILED` action failed), `created_at`, `updated_at` |

## 4. Source mapping

The following is a point-in-time record from the read-only inspection on
2026-09-22. Counts and ranges will naturally move as the source systems run;
field names and join paths are the contract that the Step 1 pipelines use.
Sample values are from a Marketing Eye-scoped record where available.
Personal profile data and monitored-page text are described, rather than
copied, so the contract does not become a second source of customer data.

| Source | Verified location | Point-in-time evidence | Target | Pipeline module |
|---|---|---|---|---|
| CompetitorScope changes | `competitors_monitoring_test.changes` | 118 documents; `detected_at` range 2026-09-08T09:58:03.907Z–2026-09-09T06:15:14.219Z | `competitor_activities` | `pipelines/competitor_activity.py` |
| CompetitorScope companies | `competitors_monitoring_test.companies` | 5 documents; exactly one has `name: "Marketing Eye"` and an ObjectId `_id` | the tenant lookup for the competitor filter | same |
| CompetitorScope competitors | `competitors_monitoring_test.competitors` | 22 documents; `updated_at` range 2026-09-04T04:48:17.178Z–2026-09-20T14:47:17.615Z | `competitors` | same |
| CompetitorScope monitoring targets | `competitors_monitoring_test.monitoring_targets` | 610 documents; `last_checked_at` is a date on 5 (range 2026-09-05T10:32:14.086Z–2026-09-09T06:24:25.595Z) and `null` on 605 | the change-to-competitor join | same |
| DCT influencer candidates | `influencer_discovery.influencer_candidates` | 296 documents; `updated_at` range 2026-08-26T05:26:01.542Z–2026-09-03T06:32:53.218Z. The Marketing Eye source subset is 252 documents. | `influencers` | `pipelines/influencers.py` |
| DCT candidate evidence | No `influencer_candidate_evidence` collection exists in `influencer_discovery` | The database lists only `influencer_candidates` and `marketing_eye_candidates`; candidate evidence is embedded in `platform_data.recent_posts`. | `influencers.evidence` | same |
| Pace AI-enriched posts | `pace_database.ai_posts` | 37 documents; `created_at` range 2026-08-07T03:45:01.824Z–2026-08-07T05:43:30.933Z; 0 documents in the 14 days ending 2026-09-22. | `trends` (aggregation, currently skipped) | `pipelines/trends.py` |

### Verified deviations from the prior draft

- The cluster reachable from this repository exposes only `admin`,
  `competitors_monitoring_test`, `influencer_discovery`, `local` and
  `pace_database`; it has no "RM Mongo" database. §4 is frozen against
  `competitors_monitoring_test`, a test database, not a production source.
  If production CompetitorScope data is on another cluster, re-verify field
  names, join paths, counts and date ranges there before trusting the Step 1
  pipelines in production. The mappings below are the durable starting point;
  counts and date ranges are point-in-time observations.
- `changes` uses Mongo `_id`, not the previously assumed `id` field.
- `changes` currently contains only `NEW_BLOG`, `NEW_PRODUCT`,
  `PRICE_CHANGE` and `PRODUCT_REMOVED`; it has no `PAGE_UPDATE` records.
- Roadmap scenario 1-D describes Brown Bag and Elevation as test tenants, but
  the live source has them as unscoped `competitors` rows, not `companies`
  rows. Both lack `company_id`; the tenant allowlist excludes them without a
  name-based denylist. The two actual source-side test-company rows have
  `p6-live-test-*.example.invalid` names and are also outside that allowlist.
- DCT has no standalone `influencer_candidate_evidence` collection and no
  stored topical-label field on a candidate. Its post evidence is nested in
  the candidate document.
- Pace `ai_posts` exists, but its entire observed volume is older than the
  14-day trend window and below the 50-post threshold. The trend pipeline
  must use the seed until that condition changes.

### 4.1 CompetitorScope `changes` → `competitor_activities`

The live join path is:

```text
changes.monitoring_target_id
  → monitoring_targets._id
  → monitoring_targets.competitor_id
  → competitors._id
  → competitors.company_id
  → companies._id
```

`competitors.company_id` is the tenant discriminator when present; neither
`changes` nor `monitoring_targets` carries a direct tenant ID. Query the
source collection `competitors_monitoring_test.companies` with the exact
filter `{name: "Marketing Eye"}` and require its single result's ObjectId
`_id`. Use that ObjectId as the sole allowlist value for
`competitors.company_id`; do not query the owned `marketing_automation`
`companies` collection during ingestion. The inspection found seven active
competitors and 31 targets under that allowlist; only 3 of those targets are
`active: true`. Only one of those competitors, Lyfe Marketing, has produced
changes so far: 13, all `NEW_BLOG`.

Brown Bag Marketing and Elevation Marketing are `competitors` rows, not
`companies` rows. In the inspected documents both have a missing
`company_id`, so the Marketing Eye allowlist already excludes them; a
company-level name denylist would be ineffective and is unnecessary. The two
source-side `p6-live-test-*.example.invalid` company rows are likewise
outside the allowlist. Step 1 must therefore test that the allowlist excludes
unscoped competitors as well as competitors attached to another company; the
Roadmap 1-D wording assumes the two named competitors are tenant rows, which
is not true of this source shape.

Across all 118 `changes` documents, the actual `change_type` values are:

| `change_type` | Count |
|---|---:|
| `NEW_BLOG` | 13 |
| `NEW_PRODUCT` | 52 |
| `PRICE_CHANGE` | 12 |
| `PRODUCT_REMOVED` | 41 |

The pipeline maps only enum values in §2. An unexpected future value is
skipped and logged with its source `_id`; an enum having no current record
does not make it invalid.

`narrative_summary` is a string on 13 of 118 changes, `null` on 38 and
missing on 67. The 13 string values are exactly the 13 Marketing Eye changes,
so the required title fallback below is untested by the demo tenant.

The required `title` is constructed without parsing free prose or splitting
sentences:

1. If `narrative_summary` is a non-empty string, use it as the title
   candidate.
2. Otherwise, use `"<change_type> detected at <url>"`, where `<url>` is the
   selected non-empty `detected_url` or `monitoring_targets.url` value.
3. If both URL fields are absent, `null` or empty, use
   `"<change_type> detected"`. Unknown or missing `change_type` is skipped by
   the rule above, so this final candidate is always non-empty.
4. If a candidate exceeds 120 Unicode code points, keep its first 117 code
   points and append `...`; otherwise preserve it unchanged.

`summary` is never used to construct `title`: its verified shape is an
incremental-diff statistic rather than a page headline.

| Source field | Verified sample value | Target | Rule |
|---|---|---|---|
| `_id` | `ObjectId` (24 hexadecimal characters) | `source.ref_id` | Stringify the ObjectId; set `source.system = COMPETITORSCOPE`. |
| `change_type` | `NEW_BLOG` | `activity_type` | Direct map for the observed values above. |
| `summary` | `NEW_BLOG: 40 line(s) added, 3 line(s) removed (3096 characters added, 222 removed).` | `summary` | Preserve the source text. It is a change summary, not a post title. |
| `narrative_summary` | 266-character narrative text on the sampled `NEW_BLOG` record | `narrative_summary` | Nullable; preserve when present. |
| `detected_url` | `https://www.lyfemarketing.com/blog` | `url` | Use this field when non-empty; otherwise use `monitoring_targets.url`. |
| `monitoring_targets.url` | `https://www.lyfemarketing.com/blog` | `url` fallback | Use only when `detected_url` is empty. |
| `detected_at` | `2026-09-09T06:13:46.962Z` | `detected_at`, `occurred_at` | `occurred_at` is the best available estimate; the source does not expose a separate occurrence time. |
| `is_simulated` | `true` | `is_simulated` | Preserve the Boolean. Marketing Eye has 12 `true` values and 1 missing field across its 13 changes; globally the source has 23 `true` and 95 missing fields. Missing means `false`. This source behavior differs from the §3.3 `false` example and the §5 `SIMULATED` source-system example; retain the source system as `COMPETITORSCOPE`. |
| `monitoring_target_id` | `ObjectId` (24 hexadecimal characters) | join input | Join to `monitoring_targets._id`; it is required to resolve the competitor and tenant. |
| `monitoring_targets.competitor_id` | `ObjectId` (24 hexadecimal characters) | join input | Join to `competitors._id`. |
| `competitors.name` | `Lyfe Marketing` | `competitor_name` | Preserve as the feed's denormalized name. |
| `competitors._id` | `ObjectId` (24 hexadecimal characters) | `competitor_id` | First upsert the owned competitor by `source = { system: COMPETITORSCOPE, ref_id: str(competitors._id) }`. On its first insertion, set `_id` to `cpt_` plus the 24-character lowercase hexadecimal source ObjectId. On every re-run, resolve by `source` and reuse that stored `cpt_` ID. |
| `competitors.website_url` | `https://www.lyfemarketing.com/` | owned competitor `website` | Use when creating or updating the owned competitor record. |
| `competitors.company_id` | `ObjectId` (24 hexadecimal characters) on a Marketing Eye competitor | tenant filter | This is the source-side tenant discriminator when present. Require membership in the Marketing Eye allowlist; a missing value fails the filter. |
| `companies.name` | `Marketing Eye` | tenant lookup only | Resolve the Marketing Eye source company ID for the allowlist. Do not use a name-based exclusion or copy source company documents into the owned database. |
| `changes` collection | Website-change records; the sampled change has an HTTPS page URL | `channel` | Set `WEBSITE` for every CompetitorScope `changes` record. This pipeline consumes website deltas only; it does not use either source-vocabulary channel registry below. |
| `narrative_summary`, `change_type`, `detected_url`, `monitoring_targets.url` | All 13 Marketing Eye changes have a non-empty `narrative_summary`; the fallback is therefore untested by this tenant | `title` | Use the deterministic 120-code-point construction above. The prior `New post: "..."` parser is not used. |

### 4.2 DCT `influencer_candidates` → `influencers`

The DCT pipeline runs even though DCT has no topic labels. It reads only
`influencer_discovery.influencer_candidates` filtered to
`company_id = "marketingeye.com.au"`, `evaluation.status = "eligible"` and a
numeric `evaluation.latest_final_score`. The observed Marketing Eye subset has
252 eligible X candidates, all with that score, `updated_at` from
2026-08-26T05:26:01.542Z through 2026-08-28T05:41:01.640Z, and scores from 30
through 70. Order candidates by final score descending, then source `_id`
ascending, and ingest at most the named `DCT_CANDIDATE_LIMIT = 25`. Candidates
that fail the filter are skipped and logged with their source `_id`.

The 25 selected records are useful in an unfiltered influencer list, but have
`topics: []`; topic-filtered queries exclude empty-topic DCT records and use
the explicitly topical seed. A sampled candidate has five embedded recent
posts and a five-figure follower count. Its public account and profile
identifiers, timestamps and exact engagement metrics are intentionally not
reproduced here.

`DCT_PLATFORM_CHANNELS` and `PACE_SOURCE_CHANNELS` are separate typed
registries because DCT `platform` and Pace `source` use different vocabularies.
Tests must assert that every documented key has an entry in its own registry.

| Source field | Verified sample value | Target | Rule |
|---|---|---|---|
| `_id` | `ObjectId` (24 hexadecimal characters) | `source.ref_id` | Stringify the ObjectId; set `source.system = DCT`. |
| `company_id` | `marketingeye.com.au` | source filter | Read only this value for the demo tenant; write the owned `company_id` `cmp_marketing_eye`. |
| `platform` | `x` on all 252 eligible Marketing Eye candidates | `channel` | `DCT_PLATFORM_CHANNELS` maps `x` → `X`. An unknown platform skips and logs the candidate; it must not receive a guessed channel. |
| `profile.display_name` | Non-empty public display name | `name` | Copy only from a candidate selected by the bounded rule above. |
| `account.handle` | Non-empty public handle | `handle` | Copy as the handle, adding `@` only if the source value lacks it. |
| `account.profile_url` | Non-empty public X profile URL | `profile_url` | Copy as-is. |
| `profile.followers` | Five-figure numeric follower count | `followers` | Copy as a number. |
| `platform_data.recent_posts[]` | 5 recent posts; source views are in the hundreds and source text and HTTPS URLs are present | `engagement_rate`, `evidence[]` | There is no direct engagement-rate field. When candidate-level `profile.followers` is numeric and greater than 0, calculate the mean of `(likes + replies + reposts) / profile.followers` across posts with all three numeric metrics. If there are no qualifying posts, or followers is missing, non-numeric or 0, set `engagement_rate` to `0.0`. Use each post's non-empty `text` and `url` to form at most three evidence entries; when none qualify, keep `evidence` empty. |
| `evaluation.latest_final_score` | `50` (observed range 30–70) | `relevance_score` | `clamp(latest_final_score / 100, 0, 1)`; sample becomes `0.50`. |
| `evaluation.score_breakdown.topic_relevance` | `6` (observed range 0–20) | ranking audit only | This is a numeric component, not a topic label. Retain it in pipeline diagnostics; do not present it as `topics`. |
| — | No source field contains topic labels | `topics` | Use an empty list for a DCT-derived record. Topic-filtered influencer results fall back to the explicitly topical seed until a separately specified topic-classification source exists. |
| — | `audience_region` is missing on all 296 source candidates | `audience_region` | Set the literal `UNKNOWN`; do not infer geography from profile text, handle or URL. |

There is no DCT evidence ledger to join. `platform_data.recent_posts` is the
only verified evidence source; its text is untrusted source content and must
not be treated as instructions by a later pipeline or agent.

### 4.3 Pace `ai_posts` → `trends`

`pace_database.ai_posts` exists, but it is currently not a usable live trend
source: the collection has 37 documents total and zero whose `created_at` is
within the 14 days ending 2026-09-22. Its observed created-at range is
2026-08-07T03:45:01.824Z–2026-08-07T05:43:30.933Z. The pipeline therefore
skips the aggregation and uses the fully seeded trend set (`is_mock: true`).

When Pace has at least 50 posts inside the 14-day window, aggregate by the
enriched `topics` array and the mapped Pace channel, not by `keywords`:

```text
$match created_at in the 14-day window
→ map source through PACE_SOURCE_CHANNELS
→ $unwind "$topics"
→ $group by "$topics" and mapped channel
```

The observed topic values are `Marketing` (11), `News` (11), `Technology`
(7), `Business` (6) and `Other` (2). Compute `mention_count` over the latest
seven days and `momentum_pct` against the preceding seven; retain up to three
sample posts for each topic.

#### Aggregate identity and upsert

Capture `window_end_date` once when the pipeline starts as that run's UTC
calendar date. Its aggregation interval is the 14-day half-open interval
`[window_end_date - 14 days, window_end_date)`. For each `(topic,
mapped_channel)` group, set `source.ref_id` to:

```text
trend:<window_end_date>:<mapped_channel>:<SHA-256(UTF-8(topic))>
```

The full lowercase hexadecimal SHA-256 digest prevents delimiters or Unicode
in a source topic from making the key ambiguous. The pipeline upserts on
`{ "source.system": "PACE", "source.ref_id": <that key> }`, setting the
aggregate fields and `computed_at` on every run, and sets a new `trd_` ID only
with `$setOnInsert`. Therefore a re-run for the same window, topic and channel
updates exactly one trend document; a new UTC window creates a distinct,
dated aggregate. A raw Pace post `_id` is never used as a trend's
`source.ref_id` because a group can contain many posts.

#### Aggregate output construction

For each dated group, `mention_count` is the count in the latest seven days
`[window_end_date - 7 days, window_end_date)`, so `window_days` is always
`7`. Let `current_count` be that count and `previous_count` be the count in
the preceding seven-day interval. Set `momentum_pct` to
`(current_count - previous_count) / max(previous_count, 1) * 100` and map it
to `direction` through `PACE_TREND_DIRECTIONS`: greater than `10` is `RISING`,
less than `-10` is `FALLING`, and every other value is `STEADY`.

Build `keywords` from the group's non-empty string `keywords[].term` values
that have a numeric `keywords[].score`: take at most five distinct terms,
ordered by their mean score descending and then their Unicode code-point order
ascending. If none qualify, use `[]`. Set `sentiment` to the mean of the
per-post signed values defined below, or `0.0` if no post has one. Select up
to three `sample_posts` newest-first by `created_at`, breaking a tie by raw
post `_id` ascending. Every Pace-derived aggregate sets `is_mock: false`; only
the seed fallback has `is_mock: true`.

The complete observed `PACE_SOURCE_CHANNELS` registry is:

| `source` | Count | `Channel` |
|---|---:|---|
| `bbc_rss` | 1 | `NEWS` |
| `duckduckgo_web` | 3 | `WEBSITE` |
| `guardian_api` | 1 | `NEWS` |
| `news_rss` | 6 | `NEWS` |
| `newsapi` | 6 | `NEWS` |
| `reddit_playwright` | 6 | `REDDIT` |
| `techcrunch_rss` | 2 | `NEWS` |
| `x_playwright` | 6 | `X` |
| `youtube_search` | 6 | `YOUTUBE` |

An unrecognized Pace `source` skips and logs that post with its source `_id`;
it must not be assigned a guessed channel or included in the aggregation.

| Source field | Verified sample value | Target | Rule |
|---|---|---|---|
| `_id` | `ObjectId` (24 hexadecimal characters) | aggregation input only | Use only to identify and log an individual raw post. Do not copy it to `trends.source.ref_id`; the aggregate identity above is the sole Pace trend reference. |
| `created_at` | `2026-08-07T05:43:30.933Z` | aggregation window | This is the authoritative window field, not the numeric crawl or publication timestamps. |
| `topics[]` | `["Business"]` | `topic`, grouping key | Unwind and group by each topic value. |
| `topic_confidence` | `0.72` | aggregation quality input | Keep only as a pipeline diagnostic until a threshold is specified. |
| `keywords[]` | one term `marketing` with score `0.55` | supplementary metadata | Do not group trends by this field; its terms are not the verified topic taxonomy. |
| `source` | 9 observed values listed in `PACE_SOURCE_CHANNELS` | `channel`, `sample_posts[].channel` | Map through `PACE_SOURCE_CHANNELS`; the unknown-value rule above applies. |
| `content_type` | `post` | sample-post metadata | Preserve only as diagnostic metadata. |
| `title`, `url` | 120-character source title and 53-character HTTPS source URL | `sample_posts[]` | Copy into the top-three sample posts only when the aggregation runs. |
| `sentiment.label`, `sentiment.score` | `positive`, `0.8` | `sentiment` | `PACE_SENTIMENT_LABELS` is complete: `positive` → `+clamp(score, 0, 1)`, `negative` → `-clamp(score, 0, 1)`, `neutral` → `0`. A missing sentiment document, missing/non-numeric score or unknown label logs a diagnostic and produces `0.0`. |

## 5. Mock seed requirements

Seed files live in `backend/app/pipelines/seed/*.json`.
They are loaded by `backend/scripts/seed_db.py`, and every seeded record is
`is_mock: true`.
At seed time, their timestamps are rebased from the fixed authored anchor to
the load time, preserving relative spacing.

| Dataset | Minimum content |
|---|---|
| `companies` | 1 (Marketing Eye), with full brand voice, 4 content pillars, 5 services and 2 ICP segments |
| `competitors` | Lyfe Marketing (real; from CompetitorScope if present, otherwise seeded without mock activities) + **Brightlane Marketing** and **Kestrel Growth Co.** (both `is_fictional: true`, each with a named fictional CEO) |
| `competitor_activities` | ≥ 45 records over the last 30 days. **Every** `ActivityType` has at least 3. Channels cover WEBSITE, LINKEDIN, X and INSTAGRAM. At least 6 records fall in the last 48 h, so the feed looks alive. Mock social, executive, campaign and promotion activity belongs only to the fictional competitors. |
| `trends` | ≥ 16 records across LINKEDIN, X, REDDIT and NEWS, mixing RISING, STEADY and FALLING. At least 4 overlap topically with competitor activity, so cross-evidence reasoning is possible. |
| `influencers` | ≥ 20 across LINKEDIN, X and YOUTUBE, with 60% AU audiences and relevance scores spread across 0.3–0.95 |
| Simulation templates | ≥ 2 templates per `ActivityType`, used by `POST /activities/simulate`; every template targets a fictional competitor and uses a `.example` URL (records are `is_simulated: true`, `source.system = SIMULATED`) |

Content rules for the seed:

- Seed text is realistic, specific and dated. No lorem ipsum, and no "Example
  Corp".
- The validator requires the reserved `.example` TLD for every fictional
  competitor website, social profile and activity URL; simulation template;
  trend sample post; and influencer profile and evidence-post URL. For
  example, `https://brightlane.example/blog/…` can never resolve to a real
  site.
- Adversarial records (prompt-injection text, defamatory bait) exist **only**
  in the eval fixtures. They are never in the demo seed.

## 6. Eval fixture snapshot

`backend/scripts/snapshot_fixture.py` exports the owned collections into
`evaluation/fixtures/intelligence_v{N}.json`, together with the eval-only
adversarial records. The eval harness loads the snapshot into a throwaway
database (`marketing_automation_eval_<run>`), either on a local `mongo:7`
container (the default, and the one CI uses) or on the dev cluster. Golden cases reference evidence IDs from a specific fixture version.
Bumping the fixture version requires re-validating the cases' `expected_evidence`.
