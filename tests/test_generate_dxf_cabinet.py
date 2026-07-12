"""
Test DXF generation for wall cabinet.

Parameters from sketch:
- Width: 600mm
- Height: 720mm
- Depth: 300mm
- LDSP 16mm
- 1 door, 2 shelves
"""
import io
import sys
from pathlib import Path

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.dxf_generator import Panel, generate_panel_dxf, optimize_layout_best
from api.panel_calculator import calculate_panels


def main():
    # Wall cabinet params
    params = {
        "cabinet_type": "wall",
        "width": 600,
        "height": 720,
        "depth": 300,
        "material": "LDSP",
        "thickness": 16,
        "doors_count": 1,
        "shelves_count": 2,
    }

    print("=" * 60)
    print("TEST: DXF Generation for Wall Cabinet")
    print("=" * 60)
    print(f"Params: {params['width']}x{params['height']}x{params['depth']} mm")
    print(f"Material: {params['material']} {params['thickness']}mm")
    print(f"Doors: {params['doors_count']}, Shelves: {params['shelves_count']}")
    print()

    # 1. Calculate panels
    print("1. PANEL CALCULATION (panel_calculator)")
    print("-" * 40)

    calc_result = calculate_panels(
        cabinet_type=params["cabinet_type"],
        width_mm=params["width"],
        height_mm=params["height"],
        depth_mm=params["depth"],
        thickness_mm=params["thickness"],
        door_count=params["doors_count"],
        shelf_count=params["shelves_count"],
    )

    print(f"Total panels: {len(calc_result.panels)}")
    for i, p in enumerate(calc_result.panels, 1):
        print(f"  {i}. {p.name}: {p.width_mm}x{p.height_mm}mm")
        if p.drilling_points:
            print(f"     Drilling: {len(p.drilling_points)} points")
    print()

    # 2. Convert to Panel objects for DXF
    print("2. PREPARE PANELS FOR DXF")
    print("-" * 40)

    panels = []
    for p in calc_result.panels:
        # PanelSpec uses edge_front/edge_back, Panel uses edge_left/edge_right
        panel = Panel(
            id=str(hash(p.name)),
            name=p.name,
            width_mm=p.width_mm,
            height_mm=p.height_mm,
            thickness_mm=p.thickness_mm,
            material=params["material"],  # from input params
            edge_top=p.edge_top,
            edge_bottom=p.edge_bottom,
            edge_left=p.edge_front,  # front -> left
            edge_right=p.edge_back,  # back -> right
            drilling_points=p.drilling_points or [],
        )
        panels.append(panel)

        edges = []
        if p.edge_top:
            edges.append("top")
        if p.edge_bottom:
            edges.append("bottom")
        if p.edge_front:
            edges.append("front")
        if p.edge_back:
            edges.append("back")
        edge_str = ", ".join(edges) if edges else "none"
        print(f"  {p.name}: edge [{edge_str}]")
    print()

    # 3. Optimize layout
    print("3. OPTIMIZE LAYOUT")
    print("-" * 40)

    sheet_width = 2800
    sheet_height = 2070
    gap_mm = 4  # for saw cut

    layout = optimize_layout_best(
        panels=panels,
        sheet_width=sheet_width,
        sheet_height=sheet_height,
        gap_mm=gap_mm,
    )

    print(f"Sheet: {sheet_width}x{sheet_height}mm")
    print(f"Gap (saw cut): {gap_mm}mm")
    print(f"Placed: {len(layout.placed_panels)} panels")
    print(f"Unplaced: {len(layout.unplaced_panels)} panels")
    print(f"Utilization: {layout.utilization_percent:.1f}%")
    print()

    for panel, x, y, rotated in layout.placed_panels:
        rot_str = " (rotated)" if rotated else ""
        print(f"  {panel.name}: pos ({x:.0f}, {y:.0f}){rot_str}")
    print()

    # 4. Generate DXF
    print("4. GENERATE DXF")
    print("-" * 40)

    dxf_bytes, _ = generate_panel_dxf(
        panels=panels,
        sheet_size=(sheet_width, sheet_height),
        optimize=True,
        gap_mm=gap_mm,
    )

    # Save
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "test_cabinet_600x720x300.dxf"
    output_file.write_bytes(dxf_bytes)

    print(f"File size: {len(dxf_bytes)} bytes ({len(dxf_bytes) / 1024:.1f} KB)")
    print(f"Saved: {output_file}")
    print()

    # 5. Analyze DXF content
    print("5. ANALYZE DXF (layers and objects)")
    print("-" * 40)

    dxf_text = dxf_bytes.decode("utf-8")

    # Count objects by type
    line_count = dxf_text.count("LINE")
    circle_count = dxf_text.count("CIRCLE")
    lwpolyline_count = dxf_text.count("LWPOLYLINE")
    mtext_count = dxf_text.count("MTEXT")

    print(f"  LINE: {line_count}")
    print(f"  CIRCLE: {circle_count}")
    print(f"  LWPOLYLINE: {lwpolyline_count}")
    print(f"  MTEXT: {mtext_count}")

    # Layers
    print()
    print("  Layers:")
    for layer in ["CONTOUR", "EDGE", "DRILLING", "TEXT", "SHEET", "DRILL_V_35", "DRILL_V_5", "DRILL_H_4"]:
        count = dxf_text.count(f"AcDbEntity\n  8\n{layer}")
        if count > 0:
            print(f"    {layer}: {count} objects")

    print()
    print("=" * 60)
    print("DONE! Open DXF in AutoCAD/LibreCAD to verify:")
    print(f"  {output_file.absolute()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
