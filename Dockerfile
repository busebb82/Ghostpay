FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8501
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN useradd --create-home ghostpay
USER ghostpay

EXPOSE 8501
CMD ["sh", "-c", "gunicorn app:app --workers 1 --threads 8 --timeout 120 --bind 0.0.0.0:${PORT}"]
