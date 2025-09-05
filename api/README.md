# API сервис (FastAPI)

Локальный запуск (Python 3.12):

1) Установите зависимости (временно):
   - `pip install fastapi uvicorn pydantic`
2) Запуск:
   - `uvicorn api.main:app --reload`
3) Swagger UI: http://localhost:8000/docs

В проде зависимости будут закреплены в общем манифесте; не коммитьте ключи/ПДн.
