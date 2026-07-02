FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
WORKDIR /app/src
EXPOSE 9000
# Replay Time Machine + API (benchmark: `python -m clearcrew.bench`)
CMD ["uvicorn", "clearcrew.replay:app", "--host", "0.0.0.0", "--port", "9000"]
