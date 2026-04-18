FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY auth.microtv.ar/backend/ /app/
COPY microtv-crm-ycc/microtv-crm-backend/docker/auth-local/seed_crm_auth.py /opt/seed/seed_crm_auth.py

RUN rm -f /app/.env

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir "psycopg[binary]" \
    && pip install --no-cache-dir .

EXPOSE 8001

CMD ["sh", "-c", "alembic upgrade head && python /opt/seed/seed_crm_auth.py && uvicorn src.main:app --host 0.0.0.0 --port 8001"]
