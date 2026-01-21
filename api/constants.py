"""
Дефолтные значения для производственных параметров.
Используются как fallback когда настройки фабрики не заданы.
"""

# === Размеры листа ===
DEFAULT_SHEET_WIDTH_MM = 2800
DEFAULT_SHEET_HEIGHT_MM = 2070

# === Толщина материалов ===
DEFAULT_THICKNESS_MM = 16.0
DEFAULT_EDGE_THICKNESS_MM = 0.4
DEFAULT_VISIBLE_EDGE_THICKNESS_MM = 1.0
DEFAULT_FACADE_EDGE_THICKNESS_MM = 2.0

# === Зазоры и отступы ===
DEFAULT_GAP_MM = 4.0  # Зазор на пропил
DEFAULT_SHELF_GAP_MM = 3.0  # Зазор полки с каждой стороны
DEFAULT_DRAWER_GAP_MM = 26.0  # Зазор ящика (13мм с каждой стороны)
DEFAULT_BACK_PANEL_INSET_MM = 10.0  # Отступ задней стенки

# === Пазы ===
DEFAULT_BACK_SLOT_WIDTH_MM = 4.0
DEFAULT_BACK_SLOT_DEPTH_MM = 10.0

# === Конструктивные ограничения ===
DEFAULT_MAX_SHELF_SPAN_MM = 600.0  # Макс. ширина полки без провиса
DEFAULT_TIE_BEAM_HEIGHT_MM = 100.0  # Высота царги

# === G-code параметры ===
DEFAULT_SPINDLE_SPEED = 18000  # об/мин
DEFAULT_FEED_RATE_CUTTING = 800  # мм/мин
DEFAULT_FEED_RATE_PLUNGE = 400  # мм/мин
DEFAULT_FEED_RATE_DRILLING = 300  # мм/мин
DEFAULT_CUT_DEPTH = 18.0  # мм
DEFAULT_SAFE_HEIGHT = 5.0  # мм
DEFAULT_TOOL_DIAMETER = 6.0  # мм
DEFAULT_STEP_DOWN = 6.0  # мм
DEFAULT_DRILL_PECK_DEPTH = 5.0  # мм
DEFAULT_DRILL_RETRACT = 2.0  # мм
DEFAULT_DRILLING_DEPTH = 12.0  # мм

# === Стандартные размеры листов (для справки) ===
STANDARD_SHEETS = {
    "ЛДСП_2800x2070": (2800, 2070),
    "ЛДСП_2750x1830": (2750, 1830),
    "МДФ_2800x2070": (2800, 2070),
    "МДФ_2440x1830": (2440, 1830),
}

# =============================================================================
# Присадка (сверление)
# Источник: ГОСТ, технические стандарты ЛДСП 16мм
# =============================================================================

# Конфирмат (евровинт 5x40/5x50)
CONFIRMAT_EDGE_OFFSET_MM = 8.0       # Отступ от края торца
CONFIRMAT_FRONT_OFFSET_MM = 50.0     # Отступ от передней кромки
CONFIRMAT_DRILL_DIAMETER_EDGE = 5.0  # Диаметр сверла в торец
CONFIRMAT_DRILL_DIAMETER_FACE = 8.0  # Диаметр сверла в пласть
CONFIRMAT_DEPTH_EDGE_MM = 50.0       # Глубина в торец
CONFIRMAT_DEPTH_FACE_MM = 11.0       # Глубина в пласть (не насквозь!)

# Система 32 (полкодержатели)
SYSTEM32_STEP_MM = 32.0              # Шаг отверстий
SYSTEM32_OFFSET_MM = 37.0            # Отступ от передней кромки
SHELF_PIN_DIAMETER_MM = 5.0          # Диаметр под полкодержатель
SHELF_PIN_DEPTH_MM = 12.0            # Глубина отверстия

# Петли (чашка 35мм)
HINGE_CUP_DIAMETER_MM = 35.0         # Диаметр чашки
HINGE_CUP_DEPTH_MM = 12.0            # Глубина чашки (не насквозь!)
HINGE_OFFSET_FROM_EDGE_MM = 100.0    # Отступ от края фасада

# Паз под заднюю стенку
BACK_SLOT_OFFSET_MM = 10.0           # Отступ от заднего края
