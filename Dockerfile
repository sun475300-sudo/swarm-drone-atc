FROM python:3.10-slim

# System deps for scientific Python + plotting
RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8050
ENV PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8

CMD ["python", "main.py", "visualize"]
