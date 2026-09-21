# Coding Conventions

> Applies to all code in this repository, whether written by people or by
> coding agents. [AGENTS.md](../AGENTS.md) covers the project structure,
> layering and workflow. This document covers **how the code is written**.
> Where the two overlap, AGENTS.md §2 (layering) wins.

---

## 1. Stack

| Layer | Technology | Why |
|---|---|---|
| Backend | Python 3.11, FastAPI, Pydantic v2, PyMongo (async) | Typed contracts at every boundary; async I/O |
| Agents | **OpenAI Agents SDK** (`openai-agents`), with MCP for data access | Structured outputs, tools, tracing |
| Frontend | **React** 18 + TypeScript | Web-page interactivity |
| Build and hosting | **Vite** (built output hosted on Vercel) | Fast dev server, optimized static build |
| Styling | **Tailwind CSS v4**, themed only with design-system tokens | Consistent, accessible UI without hand-written CSS |
| Tooling | uv, ruff, mypy, import-linter, pytest · pnpm, ESLint, Prettier, Vitest | Enforced in CI (AGENTS.md §3) |

Don't add a new library when an existing dependency or the standard library
already covers the need. A new runtime dependency needs one sentence of
justification in the PR.

## 2. Core principles

1. **Clean, obvious code.** A reader should understand a function without
   scrolling. Name things after what they mean in the domain
   (`activity_type`, `deliverable`), not how they're implemented (`data`,
   `obj`, `tmp`).
2. **Reuse before you write.** Before adding a helper, component, error class
   or model, search for an existing one: `core/`, `agents/common/`,
   `frontend/src/components/ds/`, `frontend/src/lib/`. Extend what exists
   rather than creating a parallel version.
3. **One pattern per problem.** The same kind of problem is solved the same
   way everywhere (§3). Don't introduce a second way to do data access, error
   handling, configuration or styling.
4. **Keep it simple.** Solve the problem that's in front of you, in the
   smallest change that is correct. No speculative abstractions, no
   frameworks inside the framework, no "just in case" options. If a design
   needs a diagram to explain it, it's probably too complicated for a PoC.
5. **General solutions, not special cases.** See §4. This is the most
   important rule for keeping the code scalable.
6. **Secure, scalable and explicit about failure** by default. See §7, §8
   and §9.

## 3. Unified design patterns

Use these patterns, and only these, for the problems they cover.

| Problem | Pattern | Where |
|---|---|---|
| Handling an HTTP request | **Route → service → repository**. Routes validate and delegate, services hold the logic, repositories hold the queries. | `api/routes/`, service modules, `intelligence/repositories/` |
| Data access | **Repository**: one class per collection, with typed methods that return Pydantic models | `intelligence/repositories/` |
| Wiring dependencies | **Dependency injection**: FastAPI `Depends` in the API, constructor arguments everywhere else. No module-level singletons except the cached settings and Mongo client in `core/`. | `api/deps.py` |
| Behaviour that varies by type (activity type, deliverable type, action type, trigger kind) | **Registry**: a dict or `Mapping` from enum to handler, rule or config object. Adding a type means adding an entry, not editing branches. | Next to the enum's owner |
| Pluggable integrations | **Protocol (port) + implementations (adapters)** | `connectors/base.py`, `connectors/mock/` |
| Boundaries (HTTP, MCP, agent output, seeds, config) | **Pydantic models as contracts**. Parse at the edge; pass typed objects inward. | Everywhere |
| Agents | **Declarative agent definition**: `Agent(...)` built from config, with instructions in `instructions.md`, tools as typed functions and a Pydantic `output_type` | `agents/<agent>/` |
| Frontend data | **Hooks over one API client**: TanStack Query hooks wrap `src/api/`. Components never call `fetch`. | `src/api/`, `src/hooks/` |
| Frontend rendering by type (output cards, badges) | **Component registry**: `Record<Type, Component>` | `src/features/*` |
| Styling variants | **Variant maps**: `Record<Variant, string>` of Tailwind classes, composed with `cn()` | `src/components/ds/` |

## 4. General solutions over special cases

Code must keep working when the data grows: new activity types, channels,
deliverables, competitors and tenants. The rules:

- **Dispatch on data, not branches.** When behaviour depends on a type,
  build a registry keyed by the enum. A chain of `if`/`elif` or `switch`
  statements over types grows with every new type and is easy to leave
  incomplete. A registry can be checked for completeness in one test.
- **Parse with real parsers and schemas, not regex.** Structured input goes
  through Pydantic, `json`, `urllib.parse`, `datetime.fromisoformat` or a
  Markdown/HTML parser. Natural-language understanding (intent, entities,
  tone) goes through the LLM with a structured `output_type`. Don't write
  regexes or keyword lists that only cover the examples you've seen.
- **Configuration over code.** Mappings that product people may change,
  such as feed actions, channel limits or skill allowlists, live in one
  typed config structure. Don't scatter them as literals through the code.
- **No magic values.** Enums, not strings. Named constants, not bare
  numbers.
- **Exhaustiveness is checked.** Python registries have a test asserting
  that every enum member has an entry. TypeScript registries are typed
  `Record<Enum, …>`, so a missing key is a compile error.

```python
# ✗ Special cases: every new activity type means editing this function.
def primary_action(activity: Activity) -> FeedAction:
    if activity.activity_type == ActivityType.NEW_BLOG:
        return FeedAction(action="CREATE_SIMILAR", deliverable_type="BLOG_DRAFT")
    elif activity.activity_type == ActivityType.EXECUTIVE_POST:
        return FeedAction(action="CREATE_SIMILAR", deliverable_type="CEO_POST")
    else:
        return FeedAction(action="RESPONSE_PLAN")


# ✓ General: one registry, one lookup, and a test that every ActivityType is covered.
FEED_ACTIONS: Mapping[ActivityType, FeedActionRule] = {
    ActivityType.NEW_BLOG: FeedActionRule.create_similar(DeliverableType.BLOG_DRAFT),
    ActivityType.EXECUTIVE_POST: FeedActionRule.create_similar(DeliverableType.CEO_POST),
    ActivityType.PRICE_CHANGE: FeedActionRule.response_plan(),
    # ... one entry per ActivityType
}

def primary_action(activity: Activity) -> FeedAction:
    return FEED_ACTIONS[activity.activity_type].for_activity(activity)
```

```tsx
// ✓ Frontend: the compiler enforces that every output kind has a renderer.
const OUTPUT_CARDS: Record<OutputKind, ComponentType<OutputCardProps>> = {
  RECOMMENDATION: RecommendationCard,
  DELIVERABLE: DeliverableCard,
  CLARIFICATION: ClarificationBlock,
  REFUSAL: RefusalBlock,
};
```

**The only accepted uses of regex** are parsing a fixed, formally specified
line grammar in tooling (e.g. OpenSpec headers in `scripts/ci/`), and lint
selectors. Both must be covered by tests or have a documented grammar. A
regex that tries to interpret free text, or to match "most" cases of some
input, is a special case and is not allowed.

`if` statements are fine for real control flow: guard clauses, error checks
and boolean state. The rule targets branching **over types or values that
will grow**.

## 5. Python

- **Formatting and lint:** `ruff format` + `ruff check` (the rules are in
  `pyproject.toml`), line length 100. `mypy --strict` must pass. No
  `# type: ignore` without a reason in the same comment.
- **Types:** annotate every function. Pydantic models at boundaries, and
  dataclasses (frozen where possible) for internal value objects. A bare
  `dict` never crosses a module boundary.
- **Async:** all I/O is async. No blocking calls (`requests`, `time.sleep`,
  sync PyMongo) in request or agent paths. Always bound concurrency and set
  timeouts.
- **Functions:** do one thing, and aim for 30 lines or fewer. Use early
  returns instead of nested conditionals. Use keyword-only arguments
  (`*,`) for functions with more than 2 parameters.
- **Configuration:** read only from `core/config.py` (pydantic-settings).
  No `os.getenv` elsewhere. Model names, URLs and limits are settings.
- **Logging:** use `logging.getLogger(__name__)`. Pass context through
  `extra={"ctx": {...}}` (for example `run_id` or `company_id`). No
  `print`. Never log secrets, full prompts containing personal data, or
  whole documents.
- **Naming:** `snake_case` for modules and functions, `PascalCase` for
  classes, `UPPER_SNAKE` for constants and enum members. Enum values match
  the docs verbatim.
- **Imports:** absolute (`from marketing_automation.core.errors import …`).
  No wildcard imports. Respect the import-linter layering contracts.

### OpenAI Agents SDK

- Define each agent in `agents/<agent>/agent.py` with a factory function
  (`build_strategy_agent(settings, tools) -> Agent[RunContext]`). Don't build
  agents at import time.
- Instructions live in `instructions.md`, and are rendered with the skill
  catalogue. No prompts in Python strings.
- Always set `output_type` to a Pydantic model. Never parse free-text agent
  output.
- Tools are small typed functions (`@function_tool`) or Intelligence MCP
  tools. Tools return structured data or an error object. They never raise
  into the model.
- Every run sets `max_turns`, a timeout and the per-run tool limits
  (agents-spec §1). The model name comes from settings.
- Agents only read and propose. Side effects happen in `connectors/`, after
  user approval.
- Tracing stays enabled in development. Each run's `run_id` is attached to
  its trace and logs.

## 6. Frontend: React, Vite and Tailwind

### React and TypeScript

- `strict` TypeScript. No `any`, no non-null `!` without a guard, no
  `@ts-ignore`.
- Use function components. Name them `PascalCase.tsx`, one component per
  file. Hooks are `useX.ts`. Put shared primitives in `components/ds/`, and
  feature code in `features/<feature>/`.
- **State:** server state in TanStack Query, local UI state in `useState`,
  and nothing global unless a PR justifies it. Derive values instead of
  syncing them with `useEffect`.
- **Props:** use a small, explicit props interface. Prefer composition
  (`children`, slots) over boolean-flag props.
- **Data access:** only `src/api/` calls the backend (enforced by ESLint).
  API types are generated from the backend OpenAPI export.
- **Rendering:** stable `key`s from IDs, never array indexes, for dynamic
  lists. Never use `dangerouslySetInnerHTML`. Markdown renders through the
  sanitizing renderer.

### Vite

- Environment variables are read only through `import.meta.env.VITE_*`,
  and are typed in `src/vite-env.d.ts`. Anything prefixed `VITE_` ships to
  the browser, so **it is never a secret**.
- Keep the bundle lean: import only what you use, and code-split heavy,
  rarely used panels with `React.lazy`.
- In development, the `/api` proxy targets the backend. In production,
  `VITE_API_BASE_URL` does.

### Tailwind CSS

- **Tokens only.** `src/styles/theme.css` is the single token source,
  with values from the CompetitorScope Design System. Tailwind's default
  palette, radii, shadows and font sizes are reset. `bg-primary`,
  `text-small`, `rounded-lg` and `p-2` exist. `bg-red-500` and `text-xl` do
  not.
- **No arbitrary values** (`p-[13px]`, `bg-[#f00]`). ESLint rejects them. If
  a value is missing, add a token or a named `@utility` (e.g.
  `layout-workspace`) to `theme.css`.
- **Spacing is the 8px grid:** `p-1` is 8px, `p-2` is 16px, `p-3` is 24px.
- **Class order** is kept by `prettier-plugin-tailwindcss`. Don't order
  classes by hand.
- **Variants** use a variant map composed with `cn()`, not string
  concatenation or nested ternaries:

  ```tsx
  const TONE: Record<Tone, string> = {
    favorable: "bg-secondary-light text-favorable",
    unfavorable: "bg-error/15 text-unfavorable",
    attention: "bg-warning/15 text-attention",
    muted: "bg-text-muted/15 text-text-muted",
  };
  <span className={cn("rounded-full px-1 text-small font-semibold", TONE[tone])} />
  ```

- No inline `style` and no new `.css` files, except `theme.css`.

### Accessibility (required, not optional)

- Use semantic HTML first: `button` for actions, `a` for navigation, and
  landmark and heading order that make sense.
- Every interactive element is keyboard-reachable and has a visible focus
  ring (the global `:focus-visible` style).
- Label every control. Label icon-only buttons with `aria-label`. Live
  regions (agent progress, new feed items) use `aria-live="polite"`.
- Color is never the only signal: pair it with text, icons or signs.
- `eslint-plugin-jsx-a11y` must pass, and ui-spec §6 applies.

## 7. Error handling

**Backend**

- Raise the domain errors from `core/errors.py` (`NotFoundError`,
  `ValidationError`, `ConflictError`, `UpstreamUnavailableError`). One
  exception handler maps them to the error envelope. Don't build error
  responses in routes.
- Validate at the edge: a Pydantic model rejects bad input before any logic
  runs.
- **Never swallow exceptions.** No bare `except:`. Catch `Exception` only
  at a boundary, and only to convert and log with context. Catch specific
  exceptions everywhere else.
- Wrap upstream calls (Mongo, OpenAI, MCP) with timeouts. Retry only
  idempotent operations, with capped exponential backoff. When retries run
  out, raise `UpstreamUnavailableError` with a clear message.
- Error messages are written for the user ("OpenAI request failed:
  timeout after 30 s"). Stack traces and internals go to logs, never to the
  response.
- Agent tools return `{error: {code, message}}` objects, so the model can
  recover. A run that can't recover ends as `run.failed` with a code.

**Frontend**

- `src/api/` turns every non-2xx response into an `ApiError` (code,
  message, status). Components render `message` verbatim (ui-spec §5).
- Every data region handles loading, empty and error states. An error
  boundary around each column keeps one failure from blanking the page.
- No `console.log` in committed code. Unexpected errors are reported once,
  with context.

## 8. Security

- **Secrets:** only in `.env` locally, or in the platform's secret stores
  (GitHub, Vercel). Never in code, logs, fixtures, test output or
  `VITE_*` variables. gitleaks runs in CI and pre-commit.
- **Input validation:** every external input (HTTP, MCP arguments, LLM
  output, source documents) is parsed into a typed model with bounds (max
  lengths, `limit ≤ 50`, enum membership).
- **NoSQL injection:** build Mongo filters from typed parameters inside
  repositories. Never pass a client-supplied dict or operator into a query.
- **Least privilege:** source collections are read-only. The MongoDB MCP
  runs `--readOnly`. Agents have no write tools. CORS allows only the
  configured origins.
- **LLM-specific:**
  - Treat all third-party content (competitor posts, influencer bios, tool
    results) as untrusted data, never as instructions.
  - Validate agent output against its schema and grounding rules before
    using it.
  - Side effects require explicit user approval.
- **Output safety:** never render HTML from data or LLM output.
  Markdown is sanitized. External links use `rel="noopener noreferrer"`.
- **Dependencies:** use lockfiles (`uv.lock`, `pnpm-lock.yaml`), with
  Dependabot updates reviewed like code. Don't add packages that are
  unmaintained or unknown.

## 9. Scalability

- **Stateless API.** Keep no per-user state in process memory. Sessions,
  runs and events live in MongoDB, so any instance can serve any request.
- **Bounded work per request.** Use cursor pagination, a cap on every
  query's `limit`, and projections that fetch only the needed fields. There
  are no unbounded `find()`s.
- **Indexes are part of the feature.** A new query pattern ships with its
  index (data-contract §3), created at startup.
- **Long work stays out of requests.** Agent runs stream over SSE.
  Pipelines run as jobs, not inside API calls.
- **Writes are idempotent** where they can be retried: upserts with natural
  keys, and state machines that reject invalid transitions.
- **Extension by registration.** New types, channels, connectors and skills
  are added through registries and config (§3, §4), not by editing branches.

## 10. Testing

- Test behaviour through public interfaces, not private helpers. Structure
  tests as Arrange / Act / Assert, with one behaviour per test.
- Name tests after the behaviour: `test_feed_items_are_sorted_newest_first`.
- Unit tests need no network. Integration tests are marked
  `@pytest.mark.integration` and use a throwaway database.
- Every registry has an exhaustiveness test. Every bug fix adds a failing
  test first.
- Agent behaviour is tested with the golden datasets
  ([evaluation-spec.md](evaluation-spec.md)), not by asserting exact LLM
  wording in unit tests.
- Frontend: Vitest with Testing Library. Query elements by role and label,
  the way users find them, not by class names.

## 11. Review checklist

Reviewers (and authors, before opening a PR) check:

- [ ] Reuses existing helpers, components, errors and patterns. No parallel
      version was introduced.
- [ ] No type-based `if`/`elif`/`switch` chains, and no regex over free
      text. Registries are exhaustive and tested.
- [ ] The solution is as simple as the problem allows. No speculative
      options or layers.
- [ ] Inputs are validated at the edge. Errors are domain errors with
      user-readable messages. Nothing is swallowed.
- [ ] No secrets, no client-built Mongo filters, no rendered HTML from data,
      and side effects only after approval.
- [ ] Every query is bounded, paginated where it lists, and indexed.
- [ ] Only Tailwind token utilities are used. No arbitrary values, inline
      styles or new CSS files. Accessibility requirements are met.
- [ ] Tests cover the behaviour and the failure paths.
