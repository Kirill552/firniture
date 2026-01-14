
import asyncio
import importlib
import logging
import sys

import typer

logging.basicConfig(level=logging.INFO)

app = typer.Typer()

@app.command()
def run_script(script_name: str, args: list[str] = typer.Argument(None)):
    """Runs a script from the api.scripts directory."""
    try:
        # Ensure the script name is a valid module name
        if not script_name.replace('_', '').isalnum():
            print(f"Error: Invalid script name '{script_name}'.")
            return

        module_name = f"api.scripts.{script_name}"
        print(f"Running script: {module_name}")

        # Add project root to path to allow absolute imports
        sys.path.append('.')

        script_module = importlib.import_module(module_name)

        # Check if the script has a main async function
        if hasattr(script_module, "main") and asyncio.iscoroutinefunction(script_module.main):
            # Pass the rest of the arguments to the script's main function
            if args:
                asyncio.run(script_module.main(*args))
            else:
                asyncio.run(script_module.main())
        else:
            print(f"Error: Script '{script_name}' does not have an async main function.")

    except ImportError:
        print(f"Error: Script '{script_name}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    app()

