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
    RUSENDER_SENDING_KEY_ID: str = ""  # Числовой ID ключа транзакционной отправки
    EMAIL_FROM: str = "noreply@avtoraskroy.ru"
    # Guest Capability Token (HMAC-SHA256 secret)
    GUEST_CAPABILITY_SECRET: str = ""  # Empty = no guest tokens allowed (fail closed)

    # Защита гостевой загрузки (Task 1).
    GUEST_UPLOAD_SECRET: str = ""  # HMAC secret for guest session cookies and upload grants. Fail closed if empty in prod.
    # CIDR доверенных reverse-proxy через запятую; в production значение обязательно.
    TRUSTED_PROXY_CIDRS: str = ""
    GUEST_UPLOAD_BURST_LIMIT: int = 3
    GUEST_UPLOAD_BURST_WINDOW_SECONDS: int = 600  # 10 minutes
    GUEST_UPLOAD_DAILY_LIMIT: int = 10
    GUEST_UPLOAD_DAILY_WINDOW_SECONDS: int = 86400
    GUEST_UPLOAD_CONCURRENCY_TTL: int = 60  # seconds for analysis lock
    GUEST_GRANT_TTL_SECONDS: int = 900  # 15 minutes
    VISION_PIPELINE_TIMEOUT_SECONDS: int = 45
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024  # 10 MB decoded
    MAX_BASE64_BYTES: int = 14 * 1024 * 1024  # ~14 MB for base64 field
    MAX_IMAGE_SIDE_PX: int = 8000
    MIN_IMAGE_SIDE_PX: int = 256
    MAX_IMAGE_PIXELS: int = 24 * 1000 * 1000  # 24 MP
    ALLOWED_MIME_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp", "application/pdf"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Игнорируем лишние переменные окружения


settings = Settings()
