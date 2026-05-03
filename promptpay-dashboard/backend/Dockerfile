FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    "fastapi>=0.111" \
    "uvicorn[standard]>=0.29" \
    "pandas>=2.2" \
    "pydantic>=2.7"

# Copy entire project (build context is promptpay-dashboard/)
# so that `from backend import data_loader` works
COPY backend/ ./backend/
COPY conftest.py .

# Data will be mounted at /app/data via docker-compose volume
ENV DATA_DIR=/app/data

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
