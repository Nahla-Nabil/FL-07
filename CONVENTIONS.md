# CONVENTIONS.md

Coding conventions for the sample_app codebase (Python). Kept short on purpose — this is v1,
built for a code review agent to check against, not a style-guide encyclopedia. Entries are
things that have actually caused bugs or review comments, not aspirational rules.

1. **No bare `except:`.** Always catch a specific exception type (or `Exception` at worst) and
   either handle it meaningfully or re-raise. A bare `except:` (or `except Exception: pass`)
   silently swallows real errors, including `KeyboardInterrupt`/`SystemExit`.

2. **No `print()` for diagnostics.** Use the standard `logging` module
   (`logger = logging.getLogger(__name__)`). `print()` output is invisible in production and
   can't be filtered by severity.

3. **Never hardcode secrets.** API keys, tokens, passwords, and connection strings must come
   from environment variables (`os.environ`) or a secrets manager — never a string literal in
   source.

4. **Naming.** `snake_case` for functions and variables, `PascalCase` for classes,
   `UPPER_SNAKE_CASE` for module-level constants.

5. **Type hints on public functions.** Every function that isn't prefixed `_` must have type
   hints on its parameters and return value.

6. **Docstrings on public functions/classes.** One line minimum, stating what it does — not
   restating the signature.

7. **No mutable default arguments.** Never write `def f(items=[])` or `def f(opts={})` — the
   default is shared across calls. Use `None` and assign inside the function body instead.

8. **Explicit timeouts on outbound HTTP calls.** Any `requests.*` (or similar) call must pass
   `timeout=`. A hung dependency should not be able to hang this service forever.

## Real-project conventions (from `todo-api`, added for the FL-06 real-world validation pass)

Entries 1-8 above are for this repo's own `sample_app/`. The two below come from Nahla's actual
FastAPI To-Do API project (referenced in the FL-06 spec) and were added only to run the agents
against a real diff from that project, not synthetic fixtures — see `real-world-test/` and
`build-log.md`. Written from what the real code (`auth.py`, `db.py`, `cache.py`) actually does,
not from memory or the spec's prose.

9. **Fresh client per call, never one shared global.** `get_client()`/`get_connection()` in
   `auth.py`/`db.py`/`cache.py` each open a new Supabase/Postgres/Redis client on every call
   instead of a module-level singleton. For the Supabase client specifically this isn't just
   style: the SDK's `sign_in`/`sign_out` calls store session state on the client object itself,
   so one shared client would leak one user's session into another user's concurrent request.

10. **Auth failures raise `AuthError(status_code, message)`, never a raw exception or a bare
    `HTTPException`.** `auth.py` defines `AuthError` so every auth failure reaches the handler
    registered in `main.py` and responds with a consistent `{"error": "..."}` body instead of
    FastAPI's default `{"detail": "..."}` shape. `HTTPBearer(auto_error=False)` is used
    specifically so a missing/malformed `Authorization` header lands in `require_user()` as
    `credentials=None` — handled explicitly and raised as `AuthError(401, ...)` — rather than
    FastAPI's own generic 403.
