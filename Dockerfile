FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

# Install system dependencies
    
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure data directory has proper permissions
RUN mkdir -p data

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]
