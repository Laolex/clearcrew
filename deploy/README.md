# Alibaba Cloud deployment

The Replay Time Machine runs live on **Alibaba Cloud Function Compute 3.0**
(region `ap-southeast-1`, function `clearcrew-replay`, runtime `python3.10`):

**https://clearcrw-replay-ilccmqckdu.ap-southeast-1.fcapp.run**

Try it (the API is fully public — no key, read-only):

```bash
curl https://clearcrw-replay-ilccmqckdu.ap-southeast-1.fcapp.run/healthz
curl https://clearcrw-replay-ilccmqckdu.ap-southeast-1.fcapp.run/api/runs/events-20260702-210640-n36.jsonl   # hash chain: verified, 179 events
curl "https://clearcrw-replay-ilccmqckdu.ap-southeast-1.fcapp.run/api/runs/events-20260702-210640-n36.jsonl/counterfactual?reserve_floor=40000"
```

Note: Function Compute forces `Content-Disposition: attachment` on the default
`fcapp.run` domain, so browsers download `/` instead of rendering it — the
JSON API is unaffected. The browser UI is served through a thin reverse proxy
in front of the same function (nothing but TLS + header stripping happens
there; all compute and data live on Function Compute):

**https://clearcrew.verasettle.com** — the Replay Time Machine, in-browser.

## How it's deployed

- `fc_handler.py` — the FC entrypoint: adapts Function Compute's HTTP-trigger
  event (`version: v1`, `rawPath`, base64 body) to ASGI and invokes the exact
  same FastAPI app (`clearcrew.replay:app`) that runs locally. No fork of the
  application for the cloud.
- `s.yaml` — [Serverless Devs](https://docs.serverless-devs.com/) resource
  definition (`s deploy`).

Build the code bundle (vendored wheels must match FC's Python 3.10, linux
x86_64 — including `exceptiongroup`, which pip's marker evaluation misses when
vendoring from a newer interpreter):

```bash
mkdir build && cp -r src/clearcrew src/runs build/ && cp deploy/fc_handler.py build/index.py
pip install --target build --platform manylinux2014_x86_64 --python-version 3.10 \
    --only-binary=:all: fastapi a2wsgi exceptiongroup
s deploy -y
```

The container path also works: the repo `Dockerfile` serves the identical app
via uvicorn for any container runtime, including FC custom-container.
