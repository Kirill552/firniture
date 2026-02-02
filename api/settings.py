from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Postgres
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5433
    POSTGRES_DB: str = "furniture_ai"
    POSTGRES_USER: str = "app"
    POSTGRES_PASSWORD: str = "app"

    # Redis
    REDIS_URL: str = "redis://localhost:6380/0"

    # S3 / Object Storage (локально — MinIO)
    S3_ENDPOINT_URL: str | None = "http://localhost:9002"
    S3_PUBLIC_ENDPOINT_URL: str | None = None  # Публичный URL для presigned (если отличается)
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY: str = "minio"
    S3_SECRET_KEY: str = "minio123"
    S3_BUCKET: str = "artifacts"
    S3_PRESIGNED_TTL_SECONDS: int = 900  # 15 минут

    # JWT Authentication
    JWT_SECRET: str = "CHANGE_ME_IN_PRODUCTION_super_secret_key_2026"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 30  # 30 дней сессия

    # Magic Link
    MAGIC_TOKEN_EXPIRE_MINUTES: int = 15
    FRONTEND_URL: str = "http://localhost:3000"

    # RuSender (email)
    RUSENDER_API_KEY: str = ""  # Пустой = mock режим
    EMAIL_FROM: str = "noreply@avtoraskroy.ru"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Игнорируем YC_* и другие переменные


settings = Settings()
