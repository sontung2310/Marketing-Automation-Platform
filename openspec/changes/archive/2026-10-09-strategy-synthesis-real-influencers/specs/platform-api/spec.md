## MODIFIED Requirements

### Requirement: Insights

`GET /api/trends` (filters `channels`, `direction`, `limit` default 10) SHALL sort by `momentum_pct` desc. `GET /api/influencers` (filters `topic`, `channels`, `limit` default 10) SHALL sort by `relevance_score` desc, then `followers` desc, and each item SHALL carry `avatar_url` (a URL or null). `GET /api/recommendations` (`status` default `OPEN`, `limit` default 20) SHALL return the company's persisted recommendations, newest run first, each with its `insight` and `audience`. Items SHALL carry the fixed actions `USE_TREND` "Get topic ideas" (Strategy), `DRAFT_OUTREACH` "Draft outreach" (Execution) and `DO_THIS` "Do this" (Execution), respectively.

#### Scenario: Seeded insights load
- **GIVEN** the seeded DB with no Strategy runs yet
- **WHEN** the three endpoints are called
- **THEN** trends and influencers return sorted with their actions, and recommendations return `{items: []}`

#### Scenario: Influencers are the real DCT top 10
- **GIVEN** the seeded DB after the DCT pipeline has run
- **WHEN** `GET /api/influencers` is called
- **THEN** it returns 10 items, all with `source.system = DCT` and `is_mock: false`, ordered by relevance score then followers, each with `avatar_url`
