"""Интеграционный тест генерации G-code присадки."""

import io
import zipfile

from api.drilling_gcode import (
    DrillHole,
    DrillingSide,
    HardwareType,
    PanelDrilling,
    Slot,
    generate_drilling_zip,
    generate_panel_gcode,
)


class TestDrillingIntegration:
    """Интеграционные тесты для полного флоу присадки."""

    def test_full_cabinet_drilling(self):
        """Тест присадки полного кухонного шкафа."""
        # Навесной шкаф 600x720x300
        panels = [
            # Боковина левая
            PanelDrilling(
                panel_id="side-left",
                panel_name="Боковина левая",
                width_mm=290,  # 300 - паз
                height_mm=720,
                thickness_mm=16,
                holes=[
                    # Конфирматы снизу (крепление дна)
                    DrillHole(x=8, y=50, diameter=5, depth=50,
                              side=DrillingSide.EDGE, hardware_type=HardwareType.CONFIRMAT),
                    DrillHole(x=8, y=240, diameter=5, depth=50,
                              side=DrillingSide.EDGE, hardware_type=HardwareType.CONFIRMAT),
                    # Конфирматы сверху (крепление верха)
                    DrillHole(x=8, y=670, diameter=5, depth=50,
                              side=DrillingSide.EDGE, hardware_type=HardwareType.CONFIRMAT),
                    DrillHole(x=8, y=480, diameter=5, depth=50,
                              side=DrillingSide.EDGE, hardware_type=HardwareType.CONFIRMAT),
                    # Полкодержатели (система 32)
                    DrillHole(x=37, y=200, diameter=5, depth=12,
                              side=DrillingSide.FACE, hardware_type=HardwareType.SHELF_PIN),
                    DrillHole(x=37, y=232, diameter=5, depth=12,
                              side=DrillingSide.FACE, hardware_type=HardwareType.SHELF_PIN),
                    DrillHole(x=37, y=264, diameter=5, depth=12,
                              side=DrillingSide.FACE, hardware_type=HardwareType.SHELF_PIN),
                ],
                slots=[
                    Slot(start_x=280, start_y=10, end_x=280, end_y=710, width=4, depth=10),
                ],
                order_id="test-order-1",
            ),
            # Боковина правая (зеркальная)
            PanelDrilling(
                panel_id="side-right",
                panel_name="Боковина правая",
                width_mm=290,
                height_mm=720,
                thickness_mm=16,
                holes=[
                    DrillHole(x=8, y=50, diameter=5, depth=50,
                              side=DrillingSide.EDGE, hardware_type=HardwareType.CONFIRMAT),
                    DrillHole(x=8, y=240, diameter=5, depth=50,
                              side=DrillingSide.EDGE, hardware_type=HardwareType.CONFIRMAT),
                    DrillHole(x=8, y=670, diameter=5, depth=50,
                              side=DrillingSide.EDGE, hardware_type=HardwareType.CONFIRMAT),
                    DrillHole(x=8, y=480, diameter=5, depth=50,
                              side=DrillingSide.EDGE, hardware_type=HardwareType.CONFIRMAT),
                    DrillHole(x=253, y=200, diameter=5, depth=12,
                              side=DrillingSide.FACE, hardware_type=HardwareType.SHELF_PIN),
                    DrillHole(x=253, y=232, diameter=5, depth=12,
                              side=DrillingSide.FACE, hardware_type=HardwareType.SHELF_PIN),
                ],
                slots=[
                    Slot(start_x=10, start_y=10, end_x=10, end_y=710, width=4, depth=10),
                ],
            ),
            # Верх
            PanelDrilling(
                panel_id="top",
                panel_name="Верх",
                width_mm=568,
                height_mm=290,
                thickness_mm=16,
                holes=[
                    DrillHole(x=37, y=8, diameter=8, depth=11,
                              side=DrillingSide.FACE, hardware_type=HardwareType.CONFIRMAT),
                    DrillHole(x=531, y=8, diameter=8, depth=11,
                              side=DrillingSide.FACE, hardware_type=HardwareType.CONFIRMAT),
                ],
            ),
            # Дно
            PanelDrilling(
                panel_id="bottom",
                panel_name="Дно",
                width_mm=568,
                height_mm=290,
                thickness_mm=16,
                holes=[
                    DrillHole(x=37, y=8, diameter=8, depth=11,
                              side=DrillingSide.FACE, hardware_type=HardwareType.CONFIRMAT),
                    DrillHole(x=531, y=8, diameter=8, depth=11,
                              side=DrillingSide.FACE, hardware_type=HardwareType.CONFIRMAT),
                ],
            ),
        ]

        # Генерируем ZIP
        zip_bytes, filenames = generate_drilling_zip(panels, "weihong", "cabinet-test")

        # Проверяем архив
        assert len(zip_bytes) > 1000  # Должен быть >1KB
        assert len(filenames) == 5  # 4 панели + README

        # Распаковываем и проверяем содержимое
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
            names = zf.namelist()
            assert "README.txt" in names

            # Проверяем G-code боковины
            side_left_nc = None
            for name in names:
                if "bokovina_levaya" in name:
                    side_left_nc = zf.read(name).decode('utf-8')
                    break

            assert side_left_nc is not None

            # Проверяем критичные элементы G-code
            assert "G81" in side_left_nc  # Цикл сверления
            assert "G01" in side_left_nc  # Линейное перемещение (паз)
            assert "PAZ" in side_left_nc  # Паз под заднюю стенку
            assert "D5" in side_left_nc   # Сверло 5мм
            assert "M30" in side_left_nc  # Конец программы

    def test_gcode_nc_viewer_compatible(self):
        """Тест совместимости G-code с NC Viewer."""
        panel = PanelDrilling(
            panel_id="test",
            panel_name="Test Panel",
            width_mm=400,
            height_mm=300,
            thickness_mm=16,
            holes=[
                DrillHole(x=50, y=50, diameter=5, depth=20,
                          side=DrillingSide.FACE, hardware_type=HardwareType.SHELF_PIN),
            ],
        )

        gcode = generate_panel_gcode(panel, "weihong")

        # NC Viewer требует:
        # 1. Корректные G-коды
        assert any(f"G{i:02d}" in gcode or f"G{i}" in gcode
                   for i in [0, 1, 4, 17, 21, 80, 81, 90])

        # 2. Координаты в правильном формате
        assert "X50" in gcode or "X50.000" in gcode
        assert "Y50" in gcode or "Y50.000" in gcode

        # 3. Шпиндель
        assert "S18000" in gcode
        assert "M03" in gcode

        # 4. Нет синтаксических ошибок (базовая проверка)
        lines = gcode.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('(') or line.startswith('O'):
                continue
            # Каждая строка должна начинаться с G, M, T, S, X, Y, Z, F, N или быть комментарием
            assert line[0] in 'GMTSXYZFN(' or line.startswith('%'), f"Invalid line: {line}"
