FROM python:3.12-slim

WORKDIR /app

COPY backend/pyproject.toml backend/README.md ./
COPY backend/app ./app
COPY backend/data ./data

RUN pip install --no-cache-dir -e .

COPY frontend/dist ./frontend/dist

ENV SERVE_FRONTEND_DIST=true
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
