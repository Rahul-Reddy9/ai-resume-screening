FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -m app && mkdir -p /app/storage && chown -R app /app
USER app
EXPOSE 8000 8501
# Default: API. docker-compose overrides the command for the Streamlit frontend.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
