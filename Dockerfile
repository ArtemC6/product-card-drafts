FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY cardgen ./cardgen

EXPOSE 8000
CMD ["uvicorn", "cardgen.api:app", "--host", "0.0.0.0", "--port", "8000"]
