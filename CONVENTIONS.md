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
