Technical specification · draft v2

# intervals-icu-s3-mcp

A remote MCP server for Claude.ai (web) that gives the trainer skill (a) read/write access to intervals.icu training data via the embedded upstream `hhopke/intervals-icu-mcp` project, and (b) a durable, named key/value memory store for the trainer's analysis and hints, backed by Fly.io's Tigris (S3-compatible) object storage — fronted by a self-issued OAuth 2.1 authorization server, running as a single Fly.io machine.

This spec is the sibling of the existing `datastore-mcp` (MariaDB-backed) design: same shape — one process, one machine, single-user OAuth gate, Fly GitOps deploy — different data plane (S3 instead of MariaDB) and an added upstream tool surface (intervals.icu) instead of being a bare key/value store.

- [Decisions made](#decisions)
- [Architecture](#architecture)
- [Upstream integration & abstraction layer](#integration)
- [Regression testing against upstream](#regression)
- [Configuration](#config)
- [Data model — state_* tools](#data-model)
- [MCP tool surface](#tools)
- [Authorization flow](#auth)
- [Deployment](#deploy)
- [Trade-offs](#limits)
- [Open items](#open)
- [Proposed repo layout](#layout)

## 01 Decisions made

Resolved via clarifying questions before this spec was written:

| Question | Decision |
| --- | --- |
| How to pull in upstream intervals-icu-mcp | **Plain vendored copy** (not a git submodule — see §03 revision below), tool modules imported/merged into **one process**, behind our own abstraction layer |
| How end users deploy this | **Zero command line.** Fly.io's dashboard "Deploy from GitHub" flow (paste the repo URL, click through, add secrets in the Secrets tab) — no `flyctl`, no `git`, no terminal for the person running this. This is why the submodule decision above was revisited (§03). |
| Shape of persisted trainer memory | Named key/value docs, same five `state_*` tools as datastore-mcp, now S3-backed |
| Single vs multi-athlete | Single user/athlete, same as both existing MCPs |
| Deployment topology | One Fly.io app, one always-on machine |
| S3 provider | Fly.io's own object storage (Tigris), via `fly storage create` |
| GitOps/CI | Fly's native GitHub integration (push-to-main deploy), no in-repo workflow — same as datastore-mcp |
| Which upstream tools to expose | All of them, unfiltered, including write-capable ones (no read-only restriction) |
| Implementation language | **Python/FastMCP**, not Node/TS — see §02, forced by upstream being Python |
| Upstream change management | A dedicated abstraction layer + regression test suite (§03, §04), so submodule bumps are centrally managed and breaking changes surface immediately, not at runtime |

### Auth model at a glance

Three distinct auth relationships, not to be confused with each other:

| Relationship | Mechanism | Where |
| --- | --- | --- |
| Claude.ai ⇄ this MCP | **OAuth 2.1** (self-issued, username/password login gate) | §07 |
| This MCP ⇄ intervals.icu | Static API key, **env var** (`INTERVALS_ICU_API_KEY`) | §05 |
| This MCP ⇄ S3/Tigris | Static access key/secret, **env var** (from `fly storage create`) | §05 |

Only the Claude-facing edge gets a real OAuth flow. Both backend credentials (intervals.icu, S3) are plain secrets injected via `fly secrets set` / env vars at boot — never OAuth, never committed, never put through the login form. This mirrors exactly how datastore-mcp treats its MariaDB credentials (`DB_USER`/`DB_PASSWORD` as env vars) vs. its OAuth-gated client-facing edge.

## 02 Architecture

Upstream `hhopke/intervals-icu-mcp` turned out to be a **Python 3.11+ / FastMCP ≥3.0** project (`pyproject.toml`, `src/intervals_icu_mcp/`), not Node/Express like `datastore-mcp`. It also has **no built-in authentication** for HTTP transport — its own docs (`docs/remote-deployment.md`) explicitly warn that MCP-over-HTTP has no auth and tell self-hosters to put a tunnel or reverse proxy in front. Credentials today are static env vars (`INTERVALS_ICU_API_KEY`, `INTERVALS_ICU_ATHLETE_ID`) read once at boot via `pydantic-settings`.

Consequence: this project is Python throughout. One process runs three roles, same division as datastore-mcp:

1. **OAuth 2.1 authorization server + resource server** for a single user — our own code, there is nothing to reuse from upstream here.
2. **MCP tool host** for the full upstream intervals.icu tool set, reached only through our abstraction layer (§03), never imported ad hoc.
3. **MCP tool host** for our new `state_*` S3 tools.

All three share one FastMCP app (plus its underlying Starlette ASGI app) so that in-memory OAuth state (registered clients, pending logins, issued tokens) stays in one memory space — which is why the deployment is pinned to one machine, exactly as in datastore-mcp.

Checked and confirmed: FastMCP ships `OAuthProxy`, `RemoteAuthProvider`, and provider-specific wrappers (`GitHubProvider`, `GoogleProvider`, `AzureProvider`, etc.) — all of them *delegate* real user login to an external identity provider. None of them is a self-contained username/password authorization server. So the OAuth layer here is a **custom-written provider**, ported from datastore-mcp's `SingleUserAuthProvider` logic (Node/TS) into Python/Starlette, not something FastMCP gives us for free.

### Request lifecycle

1. Client sends `POST /mcp` with a JSON-RPC body and, once authorized, a `Bearer` token.
2. Our auth middleware verifies the token against the in-memory token store; missing/expired → `401` + `WWW-Authenticate` pointing at protected-resource metadata.
3. FastMCP dispatches to the matching tool — either one of ours (`state_*`, S3-backed) or one reached through the upstream abstraction layer (intervals.icu-backed).
4. Tool result returned as MCP's normal JSON-RPC response.

## 03 Upstream integration & abstraction layer

**Revised from the original plan.** A git submodule was the first choice here, specifically to make upstream updates a one-line pointer bump. It was dropped once a deployment requirement took priority: **the person deploying this must never need a command line** — they create a Fly.io account, point Fly at this GitHub repo, add secrets by clicking in Fly's dashboard, and that's it (§09). Fly's "Deploy from GitHub" flow clones the repository the way GitHub itself would hand it to anyone — there is no guarantee it runs `git submodule update --init`, and if it silently doesn't, the vendored code is just missing at build time with no CLI available to the end user to fix it. A plain, fully-committed copy removes that failure mode entirely, for every build path (Fly's dashboard, a GitHub Actions workflow, a local `docker build`) at once.

- Upstream's source tree (everything except its own `.git` directory) is copied as-is into `vendor/intervals-icu-mcp/` and committed as ordinary tracked files.
- Our `pyproject.toml` depends on it as a local/editable path dependency (`[tool.uv.sources]` pointing at `vendor/intervals-icu-mcp`), so `import intervals_icu_mcp` resolves to the vendored tree unmodified — same import-time behavior as a submodule would have given us.
- One build-compatibility change is applied to the vendored copy's own `pyproject.toml`: `fallback-version = "0.0.0"` added under `[tool.hatch.version]`, because upstream derives its package version from git history (`hatch-vcs`), which no longer exists once `.git` is stripped. This is a standard, documented hatch-vcs option for exactly this situation — not a code change.
- **Nothing else in `vendor/` is ever hand-edited.** "Updating upstream" now means: download the latest upstream source, replace the `vendor/intervals-icu-mcp/` directory wholesale, re-apply the one `fallback-version` line, run the regression suite (§04), and commit. This is a manual step for whoever maintains this repository — not something the deploying end user ever does or needs tooling for.

### Why an abstraction layer, not a direct import everywhere

Importing `intervals_icu_mcp.tools.*` or mounting its FastMCP app directly, scattered across our codebase, means every call site is coupled to upstream's current module layout and tool names. An upstream refactor (a renamed module, a changed function signature, a tool split in two) would then break in several places at once, discovered only when something fails at runtime. Instead:

- All contact with the vendored package goes through **one module**, `src/intervals_icu_s3_mcp/upstream.py` (or a small package if it grows), which is the single place that knows upstream's actual import paths and tool-registration mechanics.
- The rest of our code (OAuth wiring, our own `server.py` composition root, tests) only ever calls into `upstream.py` — e.g. `upstream.register_tools(mcp)` or `upstream.get_mounted_app()` — never `intervals_icu_mcp.tools.activities` directly.
- Registration mechanism, decided inside `upstream.py` — two candidate approaches, to be settled once the vendored code is actually in the tree and its `server.py` internals can be read:
  - **Mount their FastMCP app into ours** (`mcp.mount(...)`) — this is what's implemented (see `upstream.py`): upstream's `server.py` builds its own complete `FastMCP("intervals_icu_mcp")` instance with tools already registered, so any tool upstream adds or removes shows up automatically the next time `vendor/` is refreshed, with zero code changes on our side. Confirmed safe: mounting only composes tools/resources/prompts at the MCP protocol layer, not Starlette routes, so there is no collision with our own `/health` route.
  - **Import and re-register tool functions individually** — the fallback, not used: more control (e.g. per-tool filtering later), but ties `upstream.py` to upstream's internal module layout.
- **Updating upstream**: replace the `vendor/intervals-icu-mcp/` directory with a fresh copy of upstream's source, re-add the one `fallback-version` line (§03 above), run the regression suite (§04), commit, push to `main`. This is what "centrally managed" means in practice now — one directory swap plus one line, checked by CI before it ever reaches production, not a live auto-upgrade of a running machine, and not a submodule pointer bump.

## 04 Regression testing against upstream

The abstraction layer (§03) tells us *where* upstream changes land; this suite tells us *whether* a given vendor refresh broke anything, without waiting to find out in production.

- **Contract/smoke tests against the vendored package itself** (`tests/test_upstream_contract.py`): for every tool we rely on, assert it still exists under the expected import path / mount point, with the expected parameter names and return shape. These are *our* tests, living in our repo, run against whatever copy currently sits in `vendor/` — not a copy of upstream's own test suite (which we don't maintain and which could drift from what we actually depend on).
- **Integration tests against our `upstream.py` abstraction** (`tests/test_upstream_integration.py`): call `mount_upstream_tools(mcp)` against a throwaway FastMCP instance and assert the full expected tool list appears, with no name collisions against our own `state_*` tools or `/health`.
- **End-to-end smoke test** (`tests/test_e2e_smoke.py`): boot the combined app in-process, list tools (confirming upstream tools are mounted) and call one `state_*` tool against a mocked S3 bucket, asserting it succeeds. This is the one test that would catch "upstream changed something and our mount silently stopped exposing tools."
- **CI gate**: this suite runs on every push and PR, and explicitly on any commit that touches `vendor/` — a vendor refresh that fails these tests must not reach `main`/deploy. Mechanically: Fly's "Deploy from GitHub" dashboard flow deploys straight off `main`, so the regression suite runs as a required GitHub Actions check (`.github/workflows/test.yml`) gating the PR/merge to `main` itself — the gate sits *before* the push that triggers Fly's deploy, not as a separate deploy-time step.
- **Not in scope**: re-testing upstream's own internal correctness (e.g. whether their intervals.icu API client parses responses right) — that's upstream's job and its own CI. Ours only checks the *contract we depend on* didn't shift under us.

### Unit tests for our own functionality

Separate from the upstream-contract suite above: every module we actually write gets ordinary unit tests, same as any other codebase — these aren't optional or an afterthought bolted onto the upstream-regression story.

- `tests/test_config.py` — env var loading/validation (`config.py`): a missing variable never raises (§13), `missing_env_vars()` reports it by name, an invalid `PORT` falls back to the default instead of crashing.
- `tests/test_server.py` — `build_app()`'s branching (§13): fully configured exposes the real tool set; missing one of ours, or missing an intervals.icu credential, serves only `check_configuration` with the right names in its `missing` list; `/health` reflects the same.
- `tests/test_auth.py` — the self-issued OAuth provider (`auth.py`): DCR issues a client id; `/authorize` with a bad redirect URI is rejected; `/login` with wrong credentials fails and right credentials completes the redirect with a code; PKCE verification at `/token`; issued tokens expire after their TTL; no refresh-token path exists.
- `tests/test_s3store.py` — the `state_*` tool implementations (`s3store.py`), against a mocked/fake S3 client (e.g. `moto` or a hand-rolled in-memory stub, not a real Tigris bucket): create/get/update/delete/list semantics, conflict-on-create-over-existing, soft-delete round-trip, `include_deleted` filtering, not-found on deleted or missing keys.
- These run in the same CI job as the upstream-contract suite (§04 above) and gate every PR, not just submodule bumps.

## 05 Configuration

All env-driven, loaded via Fly's dashboard Secrets tab in production. **Revised from datastore-mcp's pattern**: a missing or invalid variable does not crash the process at boot. See §13.

| Variable | Source | Notes |
| --- | --- | --- |
| `PUBLIC_URL` | ours | External base URL for OAuth issuer/redirect URLs |
| `PORT` | ours | HTTP listen port (8080 on Fly) |
| `OAUTH_USERNAME` / `OAUTH_PASSWORD` | ours | Gates the login form, same as datastore-mcp |
| `OAUTH_STATE_SECRET` | ours | Encrypts the persisted OAuth session blob before it's written to S3 (§16) — independent of the two above |
| `INTERVALS_ICU_API_KEY` | upstream, passthrough | Single athlete's intervals.icu API key |
| `INTERVALS_ICU_ATHLETE_ID` | upstream, passthrough | |
| `INTERVALS_ICU_DELETE_MODE` | upstream, passthrough | `safe` / `full` / `none` — decides which destructive tools upstream even *registers* |
| S3/Tigris credentials | `fly storage create` output | Bucket name + access/secret key + endpoint — exact env var names to confirm when provisioned (see Open items) |

## 06 Data model — `state_*` tools (S3/Tigris)

Same five tools and semantics as datastore-mcp's `mcp_state` table, re-implemented against object storage instead of a database table.

- **Key layout**: `state/{var_name}.json` — flat, no per-athlete prefix (single-user decision).
- **Object body** (JSON): `{"var_name", "description", "content", "created", "last_updated", "deleted"}`.
- **Soft delete only**: `state_delete` flips `deleted: true` in place (rewrite the same key) — no `DeleteObject` call is ever exposed, matching datastore-mcp's "no hard delete."
- **Tools**: `state_create`, `state_get`, `state_update`, `state_delete`, `state_list(include_deleted)` — identical argument shapes and failure semantics (conflict on create-over-existing, not-found on missing/deleted) to the MariaDB version.
- **Concurrency trade-off (new vs. datastore-mcp)**: S3 has no row locks or transactions. `state_create`'s "fail if exists" check becomes a `HeadObject`/`GetObject`-then-`PutObject` sequence — not atomic. Acceptable for a single-user, low-concurrency assistant-memory use case; documented here as a deliberate trade-off rather than fixed with e.g. conditional writes (which Tigris may or may not support — check before relying on them if this ever matters).

## 07 MCP tool surface

- **Everything** the vendored upstream package exposes (per its `docs/tools.md`), reached through our abstraction layer (§03): activities (incl. bulk create/update/delete), wellness, performance curves, periodization, training plan, gear, events, sport settings, custom items, activity messages — unfiltered, including tools that write back to the athlete's real intervals.icu account.
- Plus our 5 `state_*` tools (§06).
- Plus our own `/health` (not upstream's — see §03 on the collision) and the standard OAuth endpoint map, identical to datastore-mcp: `/.well-known/oauth-authorization-server`, `/.well-known/oauth-protected-resource/mcp`, `/register`, `/authorize`, `/login`, `/token`, `/mcp`.

## 08 Authorization flow

Ported design, not ported code (different language): same self-issued OAuth 2.1 authorization-code-plus-PKCE server, single username/password pair (`OAUTH_USERNAME`/`OAUTH_PASSWORD`), no third-party IdP. Dynamic Client Registration stays open (any client may self-register); the real access boundary is the login form. Access tokens are opaque, one-hour TTL, no refresh tokens — an expired session re-runs login. All of this state (clients, pending logins, codes, tokens) lives in-process, which is the other reason (besides upstream's own design) this stays a single machine.

**Revised**: registered clients and issued access tokens are now also persisted to S3 (§16), specifically so a machine *restart* doesn't force a full reconnect — the in-process dicts remain the sole source of truth during a request, and the single-machine constraint is unchanged; persistence only survives a restart, it does not enable a second machine to share state safely.

## 09 Deployment (Fly.io, GitOps)

| Setting | Value |
| --- | --- |
| App | one new Fly app (name TBD) |
| Region | TBD — reuse `ams` for consistency unless there's a reason not to |
| Machine count | 1 (pinned, same rationale as datastore-mcp §06/§09) |
| Size | TBD after first real boot — Python + FastMCP + httpx likely needs more than the Node app's 256MB; profile before fixing |
| Scaling | `auto_stop_machines=false`, `min_machines_running=1` |
| Storage | A Tigris bucket, created by clicking through Fly's dashboard (Object Storage), attached to this app |
| CI/CD | **Fly's "Deploy from GitHub" dashboard flow** — the end user pastes this repo's URL once, Fly builds the Dockerfile and sets up continuous deployment, no CLI involved for them (§09, §13). The regression suite (§04) runs as a required GitHub Actions check, gating what reaches `main` before Fly ever builds it — that gate is for maintainers pushing changes, not for the end user deploying their own copy. |

### Zero-CLI deployment flow

The person running their own copy of this server never installs or types anything in a terminal. The full path, detailed with screenshots-level precision in [README.md](README.md):

1. Create a Fly.io account (web signup).
2. On Fly's dashboard, "Deploy from GitHub" — paste/select this repository, Fly builds the committed `Dockerfile` and sets up continuous deployment (future pushes to `main` auto-redeploy).
3. Create a Tigris bucket by clicking through Fly's Object Storage dashboard page, attached to the new app.
4. Add the remaining secrets (`PUBLIC_URL`, `OAUTH_USERNAME`, `OAUTH_PASSWORD`, `INTERVALS_ICU_API_KEY`, `INTERVALS_ICU_ATHLETE_ID`, `INTERVALS_ICU_DELETE_MODE`) by clicking "New secret" in the app's Secrets tab.
5. Redeploy (a button click) so the app picks up the secrets, then connect from Claude.ai's Connectors settings.

This is the deployment requirement that drove the §03 revision away from a git submodule.

## 10 Trade-offs & limitations

Carried over from datastore-mcp, plus new ones specific to this project:

- No horizontal scaling — in-memory OAuth state, single machine only.
- No refresh tokens — one-hour access tokens, expiry means a fresh login.
- State resets on redeploy — registered OAuth clients/tokens, not the S3 data (which is durable).
- Open dynamic client registration — the login screen is the real boundary, not `/register`.
- `state_delete` is soft-only, as in datastore-mcp.
- S3 has no transactional create-if-absent (§06) — a documented race-condition risk, not fixed.
- "Automatic updates" from upstream means a manual vendor-directory refresh, checked by the regression suite, then a normal push (§03, §04) — not a live auto-upgrade, and no longer a one-line submodule bump either, traded away deliberately for a zero-CLI end-user deploy (§03, §13).
- The abstraction layer and regression suite catch *contract* breaks (renamed/removed/reshaped tools); they do not catch upstream behavioral changes that keep the same signature but change what the tool actually does — that class of change still needs a human skim of upstream's changelog on each bump.
- Exposing 100% of upstream's write-capable tools means anything that can reach this MCP can mutate the athlete's real intervals.icu data (delete activities, change FTP/sport settings, etc.) — a deliberate choice, flagged here for visibility since it's a meaningfully bigger blast radius than a read-only connector.

## 11 Open items

1. ~~Submodule support in Fly's GitHub integration~~ — resolved by dropping the submodule entirely (§03); no longer applicable.
2. **Exact behavior of Fly's dashboard "attach bucket to app" step** — expected to auto-inject `BUCKET_NAME`/`AWS_*` secrets the same way `fly storage create` would from the CLI, but unverified against the current dashboard UI. If it doesn't, the bucket detail page shows the same values to copy into the Secrets tab by hand — README covers both paths.
3. **Machine size** — pick after profiling the Python process's actual memory footprint under load.
4. **Regression suite scope at launch** — start with the contract/integration/e2e-smoke tests in §04; decide later whether to also pin and test against upstream's own `tests/smoke_eval.json` fixtures for extra coverage.
5. **Keeping the vendored copy current** — no automated staleness check exists yet; relies on a maintainer periodically re-vendoring (§03). Worth a reminder/cadence once this is in real use.

## 13 Graceful misconfiguration handling

**Revised from datastore-mcp's "crash immediately with a named error" pattern** (its §09 field note #1). That's the right call for a developer debugging a boot failure in Fly's logs; it's the wrong call for a non-technical person who deployed via README.md's click-only flow and has no logs they'd know how to read — a crash-looping machine with no visible reason is a dead end for them.

Instead, `config.py`'s `Settings` model has no required fields — every one of ours (`PUBLIC_URL`, `OAUTH_USERNAME`, `OAUTH_PASSWORD`, `BUCKET_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) defaults to `None` rather than raising if unset, and a malformed `PORT` silently falls back to `8080` rather than raising. `server.py`'s `build_app()` then checks, up front:

- `config.missing_env_vars(settings)` — our own required variables.
- `upstream.missing_intervals_config()` — reads upstream's own `ICUConfig` directly (via `load_config()`) to report `INTERVALS_ICU_API_KEY` / `INTERVALS_ICU_ATHLETE_ID` specifically, rather than letting a tool call fail opaquely against upstream's own HTTP client later.

If anything is missing, **no real tool is registered at all** — not partially, not with a generic error wrapper around each one. Instead the app serves `build_misconfigured_app()`: a FastMCP instance with no OAuth (there's nothing valid to gate against if the OAuth variables themselves are what's missing), one tool (`check_configuration`) that returns the exact missing variable names and what to do about them, the same list surfaced on the FastMCP `instructions` field (shown to the client/model on `initialize`), and `/health` returning `{"status": "ok", "configured": false, "missing": [...]}` instead of a bare `{"status": "ok"}` — so a deployer can check progress just by opening that URL in a browser, without connecting Claude at all.

Once everything required is present, `build_configured_app()` runs exactly as described in §02–§08 — this is purely an up-front gate, not a change to the real app's behavior.

## 14 Keeping a fork current

README.md has the end user fork this repository (rather than deploy from the upstream repo directly) so that Fly's GitHub integration has a repository they actually have push access to connect to. The cost: a fork is a frozen snapshot, so improvements to this project don't reach a deployed instance by themselves. The fix adopted is GitHub's own one-click **"Sync fork" → "Update branch"** button — this fast-forwards the fork's `main` to match upstream, which is a normal push, so Fly's existing continuous-deployment hook (set up once in §09) redeploys automatically from it. No CLI either way, but it is explicitly a manual check-in: nothing notifies the user that an update exists. Documented as a trade-off, not hidden as "automatic."

## 16 Persisted OAuth state

**Why**: with OAuth state purely in-process (§08), a machine restart — a redeploy, a crash, Fly host maintenance — wiped every registered client and issued token, forcing Claude to fully reconnect (re-run DCR, not just re-login) every time. Given that `fly.toml` already keeps the machine always-on (`auto_stop_machines = false`), restarts are infrequent, but "infrequent" isn't "never," and when it happens the failure mode was opaque to a non-technical deployer.

**What's persisted, and what isn't**: registered OAuth clients and issued access tokens are written through to S3; pending logins and authorization codes are **not**. Both of the latter are single-use and expire in minutes (`LOGIN_ID_TTL_SECONDS` / `AUTH_CODE_TTL_SECONDS` in `auth.py`) — persisting them would only help a restart landing in a multi-second window mid-login, which isn't worth the complexity. A restart in that narrow window just means redoing that one login attempt, same as today.

**Where it lives**: `state/.oauth.json`, in the same bucket and prefix the trainer's own memory uses (`s3store.py`'s `StateStore`), not a second bucket or prefix. This reuses one bucket/one set of credentials instead of provisioning a second storage concern, at the cost of needing a boundary between "the trainer's data" and "this server's own data" within that one prefix — see the dot-file rule below.

**The dot-file reserved namespace**: any `var_name` starting with `.` is rejected by `state_create`, treated as not-found by `state_get`/`state_update`/`state_delete`, and never surfaced by `state_list` (`s3store.py`'s `ReservedNameError` / `_reject_reserved`). This is enforced at the `StateStore` layer, not just in the tool wrappers, so it holds regardless of how `state_*` is called. The trainer-facing tool docstrings say so, so the model doesn't try a dot-prefixed name and get a confusing rejection.

**Encryption**: the persisted blob contains live bearer tokens, so it's encrypted with a dedicated secret, `OAUTH_STATE_SECRET` (via `cryptography`'s Fernet, key derived from the secret with SHA-256 + base64), before being written. Without this, anyone with the S3 credentials — which already grant read access to the trainer's own notes, so this isn't a new trust boundary for *that* data — would also get a live, working Claude session for free. `OAUTH_STATE_SECRET` is a third secret, independent of `OAUTH_USERNAME`/`OAUTH_PASSWORD`; rotating it just means the next load can't decrypt the old blob and degrades to a fresh one (one forced reconnect), not a crash.

**Failure handling, consistent with §13's philosophy**: every persistence operation is best-effort. A missing file, a corrupted file, a wrong-secret decrypt failure, or an unreachable bucket during `load()` all degrade to an empty in-memory state rather than raising — worst case, that's one extra reconnect, never a crash. `save()` failures are logged and swallowed the same way; the in-process dicts remain correct regardless of whether the write-through succeeded.

**Concurrency**: still one process, one machine (§02/§08/§09) — persistence does not change that. The only new race is two concurrent requests in the *same* process both triggering a write-through at once; an `asyncio.Lock` around `_persist()` in `auth.py` serializes those. No S3-level conditional-write machinery is needed.

**What this is not**: refresh tokens. Persisting the *existing* access tokens and client registrations across a restart is unrelated to adding a refresh-token grant (still deliberately unsupported, §08/§10) — an access token that outlives the process still expires at its original one-hour mark either way.

## 17 Proposed repository layout

```
pyproject.toml
src/intervals_icu_s3_mcp/
  server.py        # FastMCP instance; composition root — wires OAuth, upstream.py, and state_* tools together
  upstream.py       # the abstraction layer: the ONLY module that imports/mounts the vendored package (§03)
  auth.py           # self-issued OAuth 2.1 provider (ported from datastore-mcp's SingleUserAuthProvider)
  oauth_persistence.py # §16 — encrypted load/save of registered clients + access tokens to S3
  s3store.py         # boto3 client + state_* tool implementations; enforces the dot-file reserved namespace (§16)
  config.py          # env var loading/validation
tests/
  test_config.py                # unit tests for config.py
  test_server.py                # §13 — configured vs. misconfigured branching
  test_auth.py                  # unit tests for the OAuth provider, incl. a restart-persistence simulation (§16)
  test_oauth_persistence.py     # §16 — encrypt/decrypt roundtrip, degrade-on-missing/corrupt/wrong-secret
  test_s3store.py               # unit tests for state_* tools, mocked S3, incl. dot-file rejection (§16)
  test_upstream_contract.py     # §04 — tool existence/shape vs. vendored package
  test_upstream_integration.py  # §04 — registration via upstream.py, no collisions
  test_e2e_smoke.py             # §04 — full OAuth + one upstream tool + one state_* tool, in-process
vendor/intervals-icu-mcp/   # plain vendored copy (not a submodule, see §03), untouched except one fallback-version line
Dockerfile
fly.toml
README.md            # zero-CLI setup guide for the person deploying this
```

---
intervals-icu-s3-mcp — implemented; see README.md to deploy, this document for the design
