"""
Сервис извлечения параметров из ТЗ для мебель-ИИ.

Интеграция с YandexGPT и Vision OCR для анализа текста, изображений и эскизов.
Извлекает технические параметры мебели с уровнем уверенности.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from shared.yandex_ai import (
    YandexGPTClient,
    YandexVisionClient,
    YandexCloudSettings,
    create_gpt_client,
    create_vision_client,
)


log = logging.getLogger(__name__)


@dataclass
class ExtractedParameter:
    """Извлечённый параметр мебели."""
    name: str
    value: Any
    confidence: float
    unit: Optional[str] = None
    question: Optional[str] = None  # Вопрос для уточнения


@dataclass
class SpecExtractionResult:
    """Результат извлечения спецификации."""
    product_config_id: str
    parameters: List[ExtractedParameter]
    confidence_overall: float
    processing_time_seconds: float
    source_type: str  # "text", "image", "sketch"


class SpecExtractionService:
    """Сервис извлечения параметров из ТЗ."""
    
    def __init__(self, yc_settings: YandexCloudSettings):
        self.yc_settings = yc_settings
    
    async def extract_from_text(self, text: str) -> SpecExtractionResult:
        """Извлечь параметры из текстового ТЗ."""
        import time
        start_time = time.time()
        
        async with create_gpt_client(self.yc_settings) as gpt_client:
            prompt = self._build_text_extraction_prompt(text)
            
            log.info("Отправка запроса к YandexGPT для извлечения параметров")
            response = await gpt_client.generate_text(
                prompt=prompt,
                temperature=0.1,  # Низкая температура для структурированного ответа
                max_tokens=2000
            )
            
            log.info(f"YandexGPT ответ получен, токены: {response.usage}")
            
            # Парсим структурированный ответ
            parameters = self._parse_gpt_parameters_response(response.text)
            
            processing_time = time.time() - start_time
            
            # Общая уверенность = среднее по параметрам
            overall_confidence = (
                sum(p.confidence for p in parameters) / len(parameters)
                if parameters else 0.0
            )
            
            return SpecExtractionResult(
                product_config_id=f"pc_{int(time.time())}",
                parameters=parameters,
                confidence_overall=overall_confidence,
                processing_time_seconds=processing_time,
                source_type="text"
            )
    
    async def extract_from_image(self, image_bytes: bytes) -> SpecExtractionResult:
        """Извлечь параметры из изображения/эскиза."""
        import time
        start_time = time.time()
        
        # Сначала OCR для извлечения текста
        async with create_vision_client(self.yc_settings) as vision_client:
            log.info("Распознавание текста с изображения через Vision OCR")
            ocr_result = await vision_client.extract_text_from_image(image_bytes)
            
            log.info(f"OCR завершён, уверенность: {ocr_result.confidence:.2f}")
            
            if not ocr_result.text.strip():
                # Нет текста на изображении, возвращаем пустой результат
                return SpecExtractionResult(
                    product_config_id=f"pc_{int(time.time())}",
                    parameters=[],
                    confidence_overall=0.0,
                    processing_time_seconds=time.time() - start_time,
                    source_type="image"
                )
        
        # Затем анализ извлечённого текста
        async with create_gpt_client(self.yc_settings) as gpt_client:
            prompt = self._build_image_extraction_prompt(ocr_result.text, ocr_result.confidence)
            
            log.info("Анализ извлечённого текста через YandexGPT")
            response = await gpt_client.generate_text(
                prompt=prompt,
                temperature=0.1,
                max_tokens=2000
            )
            
            parameters = self._parse_gpt_parameters_response(response.text)
            
            # Корректируем уверенность на основе качества OCR
            for param in parameters:
                param.confidence *= ocr_result.confidence
            
            processing_time = time.time() - start_time
            overall_confidence = (
                sum(p.confidence for p in parameters) / len(parameters)
                if parameters else 0.0
            )
            
            return SpecExtractionResult(
                product_config_id=f"pc_{int(time.time())}",
                parameters=parameters,
                confidence_overall=overall_confidence,
                processing_time_seconds=processing_time,
                source_type="image"
            )
    
    def _build_text_extraction_prompt(self, text: str) -> str:
        """Создать промпт для извлечения параметров из текста."""
        return f"""
Ты — эксперт по проектированию мебели. Проанализируй техническое задание и извлеки ключевые параметры.

ВХОДНОЕ ТЗ:
{text}

ЗАДАЧА:
Извлеки следующие параметры мебели, если они указаны в ТЗ:
- Тип изделия (шкаф, стол, полка, тумба, и т.д.)
- Размеры в мм: ширина, высота, глубина
- Материал (ЛДСП, МДФ, массив, и т.д.)
- Толщина материала в мм
- Цвет/текстура
- Количество полок/ящиков
- Фурнитура (петли, направляющие, ручки)
- Особые требования

ФОРМАТ ОТВЕТА (строго JSON):
```json
{{
  "parameters": [
    {{
      "name": "тип_изделия",
      "value": "шкаф-купе",
      "confidence": 0.95,
      "unit": null
    }},
    {{
      "name": "ширина",
      "value": 2000,
      "confidence": 0.90,
      "unit": "мм"
    }},
    {{
      "name": "высота", 
      "value": 2400,
      "confidence": 0.85,
      "unit": "мм",
      "question": "Уточните высоту — указано 'стандартная', обычно 2400мм?"
    }}
  ]
}}
```

ВАЖНО:
- Если параметр не указан явно — не добавляй его
- confidence: 0.9-1.0 = уверен, 0.7-0.8 = вероятно, 0.5-0.6 = сомневаюсь
- Размеры ТОЛЬКО в мм
- Для неточных значений добавляй "question"
- НЕ придумывай данные
"""
    
    def _build_image_extraction_prompt(self, ocr_text: str, ocr_confidence: float) -> str:
        """Создать промпт для анализа текста с изображения."""
        return f"""
Ты — эксперт по проектированию мебели. Проанализируй текст, извлечённый с изображения/эскиза.

ИЗВЛЕЧЁННЫЙ ТЕКСТ (уверенность OCR: {ocr_confidence:.2f}):
{ocr_text}

ПРИМЕЧАНИЕ: Текст мог быть распознан с ошибками. Учитывай возможные опечатки и неточности.

ЗАДАЧА: Извлеки параметры мебели аналогично предыдущему заданию.

ФОРМАТ ОТВЕТА (строго JSON):
```json
{{
  "parameters": [
    {{
      "name": "parameter_name",
      "value": "parameter_value", 
      "confidence": 0.XX,
      "unit": "мм" // или null
    }}
  ]
}}
```

ВАЖНО:
- Снижай confidence из-за возможных ошибок OCR
- Если в тексте числа неразборчивы — добавляй "question"
- Фокусируйся только на чётких технических данных
"""
    
    def _parse_gpt_parameters_response(self, response_text: str) -> List[ExtractedParameter]:
        """Парсинг ответа YandexGPT в структуру параметров."""
        try:
            # Ищем JSON блок в ответе
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Пробуем парсить весь ответ как JSON
                json_str = response_text.strip()
            
            data = json.loads(json_str)
            parameters = []
            
            for param_data in data.get("parameters", []):
                param = ExtractedParameter(
                    name=param_data["name"],
                    value=param_data["value"],
                    confidence=float(param_data["confidence"]),
                    unit=param_data.get("unit"),
                    question=param_data.get("question")
                )
                parameters.append(param)
            
            log.info(f"Извлечено {len(parameters)} параметров")
            return parameters
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            log.error(f"Ошибка парсинга ответа YandexGPT: {e}")
            log.debug(f"Ответ: {response_text}")
            
            # Возвращаем дефолтный параметр для отладки
            return [ExtractedParameter(
                name="ошибка_парсинга",
                value=str(e),
                confidence=0.0,
                question="Не удалось распарсить ответ ИИ"
            )]


# Удобная фабрика
def create_spec_extraction_service(yc_settings: YandexCloudSettings) -> SpecExtractionService:
    """Создать сервис извлечения спецификаций."""
    return SpecExtractionService(yc_settings)
