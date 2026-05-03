FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir streamlit>=1.35 plotly>=5.22 pandas>=2.2 requests>=2.31

# Copy frontend source
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
