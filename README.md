# Мебель‑ИИ — mono-repo (MVP)

Облачный AI‑SaaS для мебельных фабрик: ТЗ/эскиз → параметры → RAG‑фурнитура → BOM → DXF/G‑code → ZIP → 1С.

- Backend: FastAPI (Python 3.12)
- Frontend: Next.js 15.5 / React 19 (TypeScript)
- AI: YandexGPT 5.1 Pro, Vision OCR, Embeddings
- RAG: YDB Vector Search
- CAD/CAM: FreeCAD 1.0.x, ezdxf 1.4.2
- Data: PostgreSQL 16, Redis 7.2, Yandex Object Storage

Полезно прочитать:
- `.qoder/quests/unknown-task.md` — архитектура, контракты, диаграммы
- `RDP.md` — зафиксированный стек и ограничения
- `дизайн.md` — UI‑паттерны и wizard
- `описание.md` — контекст и цели
- `.github/copilot-instructions.md` — правила для ИИ‑агентов
- `План задач.md` — чеклист работ (MVP)

## Локальная разработка (черновик)
- docker-compose поднимет Postgres, Redis, (опц.) MinIO для S3‑совместимости.
- Секреты через `.env` (не коммитить).

## Лицензия
TBD