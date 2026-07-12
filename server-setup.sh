#!/bin/bash
# Run this on the server after SSH as mebel-ai
# Usage after ssh: bash <(curl -s https://raw.githubusercontent.com/Kirill552/firniture/main/server-setup.sh) or copy paste

set -e

echo "=== Setting up mebel-ai on server ==="

mkdir -p ~/mebel-ai
cd ~/mebel-ai

if [ ! -d ".git" ]; then
  echo "Cloning main from GitHub..."
  git clone https://github.com/Kirill552/firniture.git .
  git checkout main
else
  echo "Repo already exists, pulling latest main..."
  git fetch origin
  git checkout main
  git pull origin main
fi

echo "Copying prod compose..."
cp docker-compose.prod.yml docker-compose.yml

echo "Creating .env (you need to edit it with real values)..."
if [ ! -f .env ]; then
cat > .env << 'EOL'
# PostgreSQL
POSTGRES_USER=app
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD
POSTGRES_DB=furniture_ai

# Redis
REDIS_URL=redis://redis:6379/0

# S3 / MinIO (for start use internal minio)
S3_ENDPOINT_URL=http://minio:9000
S3_REGION=us-east-1
S3_ACCESS_KEY=minio
S3_SECRET_KEY=minio123
S3_BUCKET=mebel-ai-artifacts

# AI (OpenRouter)
AI_BASE_URL=https://openrouter.ai/api/v1
AI_API_KEY=sk-or-v1-YOUR_OPENROUTER_KEY_HERE
AI_CHAT_MODEL=deepseek/deepseek-chat-v3-0324
AI_VISION_MODEL=google/gemini-2.0-flash-001
AI_EMBEDDING_MODEL=openai/text-embedding-3-small

# Auth
JWT_SECRET=CHANGE_ME_LONG_RANDOM_STRING_32_CHARS_MIN
FRONTEND_URL=http://212.22.70.186:3000

# Optional
# RUSENDER_API_KEY=
# EMAIL_FROM=noreply@avtoraskroy.ru
EOL
  echo ".env created. EDIT IT with real values!"
else
  echo ".env already exists"
fi

echo "Starting services (first time may take time to build/pull)..."
docker compose up -d --build

echo "Running migrations..."
docker compose exec -T api .venv/bin/python -m alembic upgrade head || true

echo "=== Setup complete ==="
docker compose ps
echo "Access: http://212.22.70.186:3000 (web) and :8000 (api if exposed)"
