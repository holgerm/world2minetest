FROM python:3.11-slim

WORKDIR /app

# Only copy requirements first to leverage caching
COPY requirements.txt .

RUN apt-get update && apt-get install -y wget && apt-get clean
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["python", "w2mt.py"]