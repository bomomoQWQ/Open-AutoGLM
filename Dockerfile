FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    adb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir -e .

EXPOSE 8000

ENV PHONE_AGENT_DEVICE_TYPE=adb

CMD python -m uvicorn server:app --host 0.0.0.0 --port ${PHONE_AGENT_PORT:-8000}
