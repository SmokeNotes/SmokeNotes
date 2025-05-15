FROM python:3.11-alpine

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY smokenotes_mqtt.py .

CMD ["python", "smokenotes_mqtt.py"]

