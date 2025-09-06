
import sys
import os
import FreeCAD
import Part
import Path
import Draft

def generate_gcode_from_dxf(dxf_file, gcode_file, tool_diameter=3.175, post_processor='grbl'):
    """
    Generates G-code from a DXF file in a headless FreeCAD environment.

    :param dxf_file: The absolute path to the input DXF file.
    :param gcode_file: The absolute path to the output G-code file.
    :param tool_diameter: The diameter of the tool in mm.
    :param post_processor: The name of the post-processor to use (e.g., 'grbl', 'linuxcnc').
    """
    if not os.path.exists(dxf_file):
        print(f"Error: DXF file not found at '{dxf_file}'")
        return

    # Create a new document
    doc = FreeCAD.newDocument()

    try:
        # Import the DXF file
        Draft.importDXF(dxf_file)

        # Get all objects from the active document
        imported_objects = doc.Objects

        if not imported_objects:
            print("Error: No objects were imported from the DXF file.")
            return

        # Create a Path Job
        job = Path.Job(Base=imported_objects, Name='DXF_Job')
        job.ViewObject.Proxy = None  # Disable GUI-related updates

        # Create a Tool
        tool = Path.Tool(Name='EndMill', Path=FreeCAD.getResourceDir() + 'Mod/Path/Tools/endmill.json', ToolType='endmill')
        tool.Diameter = tool_diameter
        job.addTool(tool)

        # Create a Profile operation
        profile = Path.Profile(Objects=imported_objects)
        job.addOperation(profile)

        # Set the post-processor
        job.PostProcessor = post_processor
        job.PostProcessorArgs = '--no-show-editor' # Suppress editor window

        # Export the G-code
        prog = job.toGCode()
        with open(gcode_file, 'w') as f:
            f.write(prog)

        print(f"G-code successfully generated at '{gcode_file}'")

    finally:
        # Clean up the document
        FreeCAD.closeDocument(doc.Name)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: freecadcmd <script_name>.py <input_dxf_file> <output_gcode_file>")
        sys.exit(1)

    input_dxf = os.path.abspath(sys.argv[1])
    output_gcode = os.path.abspath(sys.argv[2])

    generate_gcode_from_dxf(input_dxf, output_gcode)
