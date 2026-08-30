# Security and Secrets

## Incident: hardcoded API key in `seed_db.py`

While preparing this refactor, `backend/seed_db.py` was found to contain a
hardcoded SiliconFlow API key literal, committed to git history (verified
via `git log --all -p -- backend/seed_db.py`). This has been fixed in
this pass: the key is now read from `LLM_API_KEY` via `config.py`, same
as every other module.

**Update (2026-08-30):** this repository's history *was* rewritten before
its public release — `git filter-repo` was used, in a disposable clone
(the private/internal repository this was developed in was left
untouched), to replace the literal key value throughout every commit
before pushing to this public copy. That is the right call specifically
because this copy exists for public portfolio distribution; it would not
be an appropriate default action against a shared/collaborated branch
without the owner's explicit sign-off, since rewriting history breaks
anyone else's clone.

1. **Rotate the key** on the SiliconFlow dashboard — this is the
   effective fix regardless of whether history is scrubbed, since the
   leaked value should be treated as compromised the moment it was
   committed to a repository, public or private.
2. If other clones of the pre-rewrite history exist (e.g. the original
   private/internal repository), the literal key value is still present
   there; this rewrite only affects the public copy.

## Current secret-handling posture

- All credentials load from environment variables via `python-dotenv`
  (`backend/.env`, gitignored), never from source.
- `backend/.env.example` documents the one required variable
  (`LLM_API_KEY`) without a real value.
- `config.py` centralizes every place a secret is read, so a future
  audit only needs to check one file.

## Other notes carried over from the original implementation

- `CORSMiddleware` allows all origins (`allow_origins=["*"]`) — flagged in
  the original code's own comment as needing restriction before
  production use; not changed here since it's a deployment-environment
  decision, not an agent-architecture one.
- Session identity is the caller's IP address (`request.client.host`),
  with no authentication. This is adequate for a local/demo deployment
  but means: (a) sessions are not private across users sharing an IP/NAT,
  and (b) they are trivially reset by changing IP. Worth revisiting
  (e.g. a signed session cookie or bearer token) before any deployment
  handling real trip/budget data. Now that session state also includes
  `trip_constraints` (previously it was just chat history), the
  practical impact of this weak session boundary is slightly larger than
  before — noted here rather than silently left as-is.

## Third-party API calls

The `local_info` agent calls two free, unauthenticated public APIs
(Open-Meteo geocoding + forecast). No API key is transmitted, and query
parameters are limited to city names and ISO dates supplied via the
already-validated `trip_constraints` slot values — there is no
user-controlled free-text field passed directly into a URL beyond the
city name itself, which is sent as a normal query parameter (via
`requests`' own encoding, not string-concatenated), so standard
injection risk here is low. If a real (keyed) flight/hotel/visa provider
is integrated later (see
[04-tools-and-integrations.md](04-tools-and-integrations.md)), its
credentials should follow the same `config.py`/`.env` pattern used for
`LLM_API_KEY`.
