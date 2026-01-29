"""
Правила расчёта количества фурнитуры.

Содержит бизнес-логику для определения:
- Количества петель по высоте и весу двери
- Длины направляющих по глубине корпуса
- Позиций петель по высоте фасада

Источники правил:
- Blum каталог 2024-2025
- Boyard рекомендации
- Отраслевые стандарты мебелестроения
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HingeCalculation:
    """Результат расчёта петель."""
    count: int
    positions_mm: list[float]  # Y-координаты от верха фасада
    notes: list[str]


@dataclass
class SlideCalculation:
    """Результат расчёта направляющих."""
    length_mm: int  # Длина направляющих (округлённая до 50мм)
    pairs_count: int  # Количество пар
    notes: list[str]


def calculate_hinge_count(
    door_height_mm: float,
    door_weight_kg: float | None = None,
) -> int:
    """
    Расчёт количества петель по высоте и весу двери.

    Правила (Blum каталог 2024-2025):
    - до 500мм и до 8кг: 2 петли
    - до 900мм и до 12кг: 2 петли
    - до 1200мм и до 17кг: 3 петли
    - до 1600мм и до 20кг: 3-4 петли
    - до 2000мм и до 25кг: 4-5 петель

    Args:
        door_height_mm: Высота двери в мм
        door_weight_kg: Вес двери в кг (опционально)

    Returns:
        Количество петель
    """
    # Расчёт по высоте
    if door_height_mm <= 500:
        count_by_height = 2
    elif door_height_mm <= 900:
        count_by_height = 2
    elif door_height_mm <= 1200:
        count_by_height = 3
    elif door_height_mm <= 1600:
        count_by_height = 4
    elif door_height_mm <= 2000:
        count_by_height = 4
    else:
        count_by_height = 5

    # Расчёт по весу (если указан)
    if door_weight_kg is not None:
        if door_weight_kg <= 8:
            count_by_weight = 2
        elif door_weight_kg <= 12:
            count_by_weight = 2
        elif door_weight_kg <= 17:
            count_by_weight = 3
        elif door_weight_kg <= 22:
            count_by_weight = 4
        else:
            count_by_weight = 5

        # Берём максимум из двух расчётов
        return max(count_by_height, count_by_weight)

    return count_by_height


def calculate_hinge_positions(
    door_height_mm: float,
    hinge_count: int,
    top_margin_mm: float = 100.0,
    bottom_margin_mm: float = 100.0,
) -> list[float]:
    """
    Расчёт Y-позиций петель по высоте фасада.

    Петли распределяются равномерно с отступами от краёв.
    Позиции указываются от ВЕРХА фасада.

    Args:
        door_height_mm: Высота фасада
        hinge_count: Количество петель
        top_margin_mm: Отступ от верхнего края
        bottom_margin_mm: Отступ от нижнего края

    Returns:
        Список Y-координат от верха фасада
    """
    if hinge_count < 2:
        raise ValueError("Минимум 2 петли на дверь")

    if hinge_count == 2:
        return [top_margin_mm, door_height_mm - bottom_margin_mm]

    # Для 3+ петель — равномерное распределение
    usable_height = door_height_mm - top_margin_mm - bottom_margin_mm
    spacing = usable_height / (hinge_count - 1)

    positions = []
    for i in range(hinge_count):
        y = top_margin_mm + i * spacing
        positions.append(round(y, 1))

    return positions


def calculate_hinges(
    door_height_mm: float,
    door_weight_kg: float | None = None,
    top_margin_mm: float = 100.0,
    bottom_margin_mm: float = 100.0,
) -> HingeCalculation:
    """
    Полный расчёт петель для двери.

    Args:
        door_height_mm: Высота двери
        door_weight_kg: Вес двери (опционально)
        top_margin_mm: Отступ сверху
        bottom_margin_mm: Отступ снизу

    Returns:
        HingeCalculation с количеством и позициями
    """
    count = calculate_hinge_count(door_height_mm, door_weight_kg)
    positions = calculate_hinge_positions(
        door_height_mm, count, top_margin_mm, bottom_margin_mm
    )

    notes = []
    if door_height_mm > 1500:
        notes.append("Высокая дверь: рекомендуется проверить вес")
    if count >= 4:
        notes.append(f"Использовать {count} петель для надёжности")

    return HingeCalculation(
        count=count,
        positions_mm=positions,
        notes=notes,
    )


def calculate_slide_length(cabinet_depth_mm: float) -> int:
    """
    Расчёт длины направляющих по глубине корпуса.

    Формула: глубина - 50мм, округлить до 50мм вниз.
    Стандартные длины: 250, 300, 350, 400, 450, 500, 550, 600 мм.

    Args:
        cabinet_depth_mm: Глубина корпуса в мм

    Returns:
        Длина направляющих в мм
    """
    raw_length = cabinet_depth_mm - 50

    # Округление до 50мм вниз
    length = int(raw_length // 50) * 50

    # Минимальная длина 250мм
    return max(250, length)


def calculate_slides(
    cabinet_depth_mm: float,
    drawer_count: int,
) -> SlideCalculation:
    """
    Полный расчёт направляющих для ящиков.

    Args:
        cabinet_depth_mm: Глубина корпуса
        drawer_count: Количество ящиков

    Returns:
        SlideCalculation с длиной и количеством
    """
    length = calculate_slide_length(cabinet_depth_mm)

    notes = []
    if length < 350:
        notes.append("Короткие направляющие: ограниченный доступ к содержимому")
    if drawer_count > 4:
        notes.append("Много ящиков: проверить распределение нагрузки")

    return SlideCalculation(
        length_mm=length,
        pairs_count=drawer_count,
        notes=notes,
    )


def estimate_door_weight(
    width_mm: float,
    height_mm: float,
    thickness_mm: float = 16.0,
    material: str = "ЛДСП",
) -> float:
    """
    Примерный расчёт веса двери.

    Плотности материалов (кг/м³):
    - ЛДСП: 650-700
    - МДФ: 700-800
    - Массив: 500-800 (зависит от породы)

    Args:
        width_mm: Ширина
        height_mm: Высота
        thickness_mm: Толщина
        material: Материал

    Returns:
        Примерный вес в кг
    """
    # Плотности в кг/м³
    densities = {
        "ЛДСП": 680,
        "МДФ": 750,
        "ДСП": 650,
        "массив": 600,
        "фанера": 550,
    }

    material_lower = material.lower()
    density = 680  # default ЛДСП

    for key, value in densities.items():
        if key.lower() in material_lower:
            density = value
            break

    # Объём в м³
    volume_m3 = (width_mm / 1000) * (height_mm / 1000) * (thickness_mm / 1000)

    return round(volume_m3 * density, 2)
