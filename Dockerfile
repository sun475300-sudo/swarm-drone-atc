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

# 보안: 비루트 사용자로 전환 — 컨테이너 탈출 시 호스트 root 노출 방지
# (Dockerfile.reproducible 과 동일 UID 1000 으로 정렬, helm runAsUser 와 일치)
RUN useradd --system --create-home --uid 1000 sdacs && \
    chown -R sdacs:sdacs /app
USER sdacs

EXPOSE 8050
ENV PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8

CMD ["python", "main.py", "visualize"]
