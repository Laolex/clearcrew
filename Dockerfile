# The frontend is built here rather than committed, so dist/ cannot drift from
# web/src. If this stage is skipped, replay.py falls back to the legacy console.
FROM node:20-slim AS web
WORKDIR /app
COPY web/ web/
COPY src/clearcrew/static/ src/clearcrew/static/
WORKDIR /app/web
RUN npm ci && npm run build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
COPY --from=web /app/src/clearcrew/static/dist src/clearcrew/static/dist
WORKDIR /app/src
EXPOSE 9000
# Replay Time Machine + API (benchmark: `python -m clearcrew.bench`)
CMD ["uvicorn", "clearcrew.replay:app", "--host", "0.0.0.0", "--port", "9000"]
