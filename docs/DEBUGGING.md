# Debugging Notes

Bugs found and fixed during development, in the order encountered. Each was caught by manual testing against real data or by reading actual error output — not guessed at. See `AI_PROMPTS.md` for the fuller narrative tying these to specific prompts.

## 1. Nonsensical partial-index expression (caught before running)

`app/models.py` — an early draft of the "one active allocation per employee" constraint had a stray `postgresql_where=(mapped_column := None) or None` walrus expression left over from an aborted approach. Caught on self-review before ever executing it; replaced with proper `Index(..., sqlite_where=text("allocation_status = 'active'"), postgresql_where=text("allocation_status = 'active'"))`.

## 2. `alternate_zone_used` mislabeled when no preference existed

**Symptom:** Allocating a seat for the very first employee on a brand-new project (no teammates seated yet) returned `"Preferred zone was full; an alternate zone was used"` — misleading, since there was no preference to begin with.

**Root cause:** `best_seat_for_employee()` in `app/services/allocation.py` fell through to the "anywhere in the building" branch and unconditionally set `alternate_zone_used=True`, without checking whether a real preference (explicit or teammate-derived) had actually been overridden.

**Fix:** Track `had_preference = preferred_floor is not None or preferred_zone is not None or zone_pref is not None` and only flag `alternate_zone_used` when a real preference was overridden.

**How found:** Manual `curl` smoke test, reading the returned `message` field.

## 3. Seed script double-allocated seats (`IntegrityError`)

**Symptom:** `python seed.py` crashed partway through with `sqlite3.IntegrityError: UNIQUE constraint failed: seat_allocations.seat_id`.

**Root cause:** `allocate_seats()` maintained two separate Python data structures referencing the *same* `Seat` objects — a per-zone dict (`seats_by_zone`) and a shuffled flat "overflow pool" list. Popping a seat from one didn't remove it from the other, so the same seat could be handed to two different employees.

**Fix:** Rewrote to a single shared per-zone bucket (`seats_by_zone`) that both the home-zone and overflow paths pop from — a seat can only ever be in one bucket, so it can only be popped once.

**How found:** Reading the traceback and the SQL parameters it printed (repeated `seat_id` across different `employee_id`s in the failing `INSERT`).

## 4. Seed script produced a misleading default employee list

**Symptom:** The default (unsorted, id-ascending) Employees page view opened on 90 consecutive rows all marked "Inactive / Pending" — looked like broken seed data at a glance.

**Root cause:** `create_employees()` used `status = INACTIVE if i <= INACTIVE_EMPLOYEES else ACTIVE`, so the first 90 employee IDs were always the inactive ones.

**Fix:** `random.sample(range(1, TOTAL_EMPLOYEES + 1), INACTIVE_EMPLOYEES)` to scatter inactive IDs across the full range.

**How found:** Playwright screenshot of the Employees page during frontend verification.

## 5. AI assistant couldn't resolve common names at 5,000-employee scale

**Symptom:** "Where is Kristen Weeks seated?" returned "I couldn't identify that employee" despite Kristen Weeks existing and being seated.

**Root cause:** `_find_employee_by_name_or_email()` matched single words (`"Kristen"`) against `Employee.name ILIKE '%word%'` and only accepted the match if it was unique — with 5,000 randomly generated names, a single first or last name is almost never unique.

**Fix:** Extract full capitalized-phrase candidates via `PROPER_NOUN_RE` (matches runs like `"Kristen Weeks"`) and try those first, longest first, before falling back to single-word matching.

**How found:** Manual `curl` testing against the real seeded dataset — the pytest fixtures only ever create 1-2 employees, so this ambiguity never appears in the automated suite (a documented test-coverage gap, see `docs/TESTING.md`).

## 6. AI intent misrouting: "sitting near" caught by the wrong branch

**Symptom:** "Who is sitting near Kristen Weeks?" returned a plain seat lookup instead of a list of nearby teammates.

**Root cause:** The generic seat-lookup intent check (`any(k in q_low for k in ["where is", "seated", "seat of", "sitting"])`) ran *before* the more specific "nearby teammates" check, and both matched on the word "sitting".

**Fix:** Reordered the intent checks so "near me / sitting near / nearby / teammates" is evaluated first.

**How found:** Same manual testing pass as #5.

## 7. `qs()` helper broke `next build` type-check

**Symptom:** `next build` failed: `Argument of type 'EmployeeListParams' is not assignable to parameter of type 'Record<string, ...>'. Index signature for type 'string' is missing.`

**Root cause:** TypeScript interfaces without an explicit index signature aren't structurally assignable to `Record<string, ...>` parameter types, even with matching value types.

**Fix:** Loosened `qs()`'s parameter type to `object` and cast internally with `Object.entries(params as Record<string, unknown>)`.

## 8. Missing Suspense boundary for `useSearchParams`

**Symptom:** `next build` failed with "Missing Suspense boundary with useSearchParams" on the Employees page (which reads `?project_id=` from the "View team →" links on the Projects page).

**Fix:** Split the page into a `Suspense`-wrapped default export and an inner `EmployeesPageContent` component that actually calls `useSearchParams()`.

## 9. Next.js dev server hung after editing `next.config.ts` live

**Symptom:** After editing `next.config.ts` (adding `turbopack.root`) while `next dev` was already running, the dev server pegged at 417% CPU and stopped responding to any request (curl hung, Playwright timed out on `page.goto`).

**Root cause:** Turbopack's hot-restart-on-config-change path hit a `SyntaxError: Invalid or unexpected token` while regenerating the RSC manifest, leaving the process in a broken but still-running state (visible in `/tmp/nextdev.log`).

**Fix:** `pkill -9` the stuck process, `rm -rf .next`, restart clean. Not a code bug — noted here because it cost real debugging time and the fix (kill + clean restart, not "fix the config") is the generalizable lesson.

## 10. `psycopg2-binary` had no wheel for this environment

**Symptom:** `pip install -r requirements.txt` failed compiling `psycopg2` from source (`pg_config executable not found`).

**Fix:** Switched to `psycopg[binary]>=3.2.10` (psycopg3), which ships prebuilt wheels for the target platforms; updated the `postgresql+psycopg://` DSN scheme accordingly.

## 11. Docker build transient failure (infra, not code)

One `docker compose build` run failed with `ResourceExhausted: cannot allocate memory` during `apt-get install` inside the backend image — a Docker Desktop VM memory-limit issue, not a Dockerfile problem. Resolved by retrying the build after the memory pressure cleared; confirmed by rebuilding both images successfully and running the full stack end-to-end against real Postgres.

## 12. Render free-tier Postgres: external connections fail at the TLS layer

**Symptom:** `sqlalchemy.exc.OperationalError: ... SSL connection has been closed unexpectedly` when connecting to Render's Postgres via its **external** connection string — both from inside a Render-hosted container and from an unrelated machine on the public internet. Raw TCP to port 5432 succeeded (`nc -zv` connected); only the TLS handshake failed, so it wasn't a firewall block.

**Root cause:** unconfirmed (Render-side proxy behavior on the free tier) — not something fixable from the client side; explicit `sslmode=require` didn't help either.

**Workaround:** use the **internal** connection string instead — reachable only from services in the same Render account/region, which is exactly what a same-account web service + Postgres pair needs anyway. This is what the deployed backend uses (`DATABASE_URL` set to the internal DSN).

**Follow-on constraint:** because external Postgres access didn't work, remote one-time seeding couldn't use a local `python seed.py` run pointed at the external DSN. Render's free tier also blocks both one-off Jobs and `pre-deploy-command` ("Commands can only run on paid instance types"), and `render ssh` requires either an interactive TTY (unavailable in this session) or a registered local SSH key (not set up). Worked around by adding a temporary token-protected `POST /admin/seed` endpoint that reuses the already-running app's internal DB connection, calling it once over HTTPS, then removing the endpoint — see the git history for the two bracketing commits.

## 13. Live Anthropic key returns 400, not 401

**Symptom:** After wiring a real `ANTHROPIC_API_KEY` into the deployed backend, `POST /ai/query` still returned the deterministic (non-Claude) answer. Logs showed `POST https://api.anthropic.com/v1/messages "HTTP/1.1 400 Bad Request"` rather than a `401` — easy to misread as an invalid/malformed key.

**Root cause:** the key itself was valid; the linked Anthropic account had no credit balance. Anthropic returns `400 invalid_request_error` with the message *"Your credit balance is too low to access the Anthropic API"* for this case, not a `401` or `403`.

**How found:** reproduced the exact call locally with the same key (via `Anthropic().messages.create(...)`) and printed the exception message — Claude's own client-side exception surfaces the API's JSON error body verbatim, which named the real cause immediately.

**Not fixed in code** — this requires adding billing/credits in the Anthropic Console. The app's fallback path already handles it correctly: `answer_with_llm_or_fallback()` catches the exception and returns the rule-based answer instead of erroring, so the endpoint stayed fully functional (`200 OK`) throughout.
