# Архитектура — кратко

См. подробности в `.qoder/quests/unknown-task.md` (§2–7, 10–11, 14, 16, 18).

## Компоненты
- Backend (FastAPI, Python 3.12)
- Frontend (Next.js 15.5, React 19)
- AI (YandexGPT, Vision OCR, Embeddings)
- RAG (YDB Vector Search)
- CAD/CAM (FreeCAD, ezdxf)
- Хранилища (PostgreSQL 16, Redis 7.2, Object Storage)
- 1С (OData/HTTP)

## Диаграммы
- Архитектура, доменная модель, пайплайн и состояния CAM — см. `unknown-task.md`.

## Контракты API (v1)
- `/api/v1/spec/extract`
- `/api/v1/spec/validate`
- `/api/v1/validation/approve`
- `/api/v1/hardware/select`
- `/api/v1/cam/dxf`, `/api/v1/cam/gcode`
- `/api/v1/integrations/1c/export`

## Принципы
- Все параметры — в мм. Русский язык.
- ПДн не передавать в LLM; пресайн-ссылки TTL ≤ 15 мин; аудит источников.