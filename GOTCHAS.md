# Gotchas — the sharp edges we actually hit

Documented so the next builder doesn't. Every one of these cost us real time
during the hackathon; none of them is in the official docs in a place you'd
find before it bites.

## Alibaba Cloud Function Compute 3.0

1. **The function URL does not speak WSGI, whatever the HTTP-handler docs
   say.** Deploy `def handler(environ, start_response)` per the docs and every
   request 502s with `'FCContext' object is not callable` — the URL trigger
   delivers an **API-Gateway-style JSON event** (`{"version":"v1","rawPath":…,
   "body":…,"isBase64Encoded":…}`) into the *event*-handler signature.
   Fix: a ~60-line event→ASGI adapter (`deploy/fc_handler.py`) that turns the
   event into an ASGI scope and runs the same FastAPI app unmodified.
2. **Vendored wheels: pip's dependency-marker evaluation misses
   `exceptiongroup`.** Building the code bundle on Python 3.12 with
   `pip install --target … --python-version 3.10` skips `exceptiongroup`
   (anyio needs it only on <3.11, and pip evaluates markers against the
   *running* interpreter). Runtime: `ImportModuleError: No module named
   'exceptiongroup'`. Fix: name it explicitly in the vendoring install.
3. **FC forces `Content-Disposition: attachment` on the default
   `fcapp.run` domain.** Your HTML downloads instead of rendering; API JSON is
   unaffected; you cannot override the header from inside the function (we
   tried — FC rewrites it). Fix: any custom domain / reverse proxy in front.
4. **`instanceConcurrency` is rejected for managed Python runtimes** (custom
   runtimes only). The deploy error doesn't say that; it 502s later.
5. **`s logs` needs SLS permissions your RAM user may not have**
   (`log:CreateProject` denied). Fastest blind-debug loop instead:
   `s invoke -e '<synthetic HTTP event JSON>'` prints the traceback directly.
6. **Design the FC surface read-only, or don't use FC.** Our trigger is
   `methods: [GET, HEAD]` (`deploy/s.yaml`) and that is not a limitation we
   worked around — it's the only reason serverless fits. Replay is a pure fold
   over an archived log, so any instance can serve any request. The corollary
   bit us when we tried to host an interactive sandbox on the same function:
   in-memory session state does not survive a platform that can cold-start,
   scale out, and recycle instances between two of a user's clicks. Anything
   stateful needs the state in the log (or a store), not the process.

## Qwen Cloud / DashScope

7. **Set your SDK timeout above the monolith's worst legitimate call.** Our
   single-prompt baseline reasons over an entire batch in ONE ~140s request; a
   "sensible" 120s client timeout made the *baseline* look broken and nearly
   corrupted a benchmark comparison. (Also an argument for societies of small
   calls over monoliths, operationally.)
8. **`enable_thinking: false` on qwen3.7-plus** is what makes the cheap-tier
   triage fast; without it the latency gap between tiers mostly disappears.
9. **Free-tier credits are a deadline, not a budget — and a benchmark you
   can't re-run is a benchmark you can't fix.** The free Model Studio quota is
   generous enough that you stop thinking about it, then it runs out. Ours did,
   and every remaining gap in the comparison table became permanently
   un-fillable: a benchmark number you want to re-cut, a baseline you want to
   re-archive, an experiment a reviewer asks for — all of it needs the API the
   quota just closed. Two things follow. Budget the runs you *know* you'll want
   before the quota decides for you. And treat every completed run as the last
   one you'll ever get: archive it whole (see #11), because "we'll just re-run
   it" quietly stops being true at a moment you don't get to pick.

## Event-sourcing honesty traps

10. **Never retro-hash old runs.** When we added hash chaining, already-archived
    runs stayed unhashed and the UI labels them "recorded before hash chaining —
    replayable, not tamper-evident." Fabricating provenance for old data is the
    exact failure mode this system exists to prevent.
11. **The bench must archive per-payout verdicts, not just aggregates.** Our
    monolith's individual decisions were printed and discarded for days —
    which is itself the thesis (opaque systems leave nothing to audit), but it
    also meant we couldn't build a "why did the monolith fail" view for those
    runs. If you compare systems, archive everything both decide. This one
    compounds with #9: the discarded verdicts became unrecoverable the day the
    quota ran out, since re-running was the only way back.
