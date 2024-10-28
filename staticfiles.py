import os
import shutil
import uuid
from pathlib import Path

OUTPUT_DIR = Path("output")  # Directory where files will be stored

# Ensure the output directory exists
OUTPUT_DIR.mkdir(exist_ok=True)


def store_static_file(input_path: Path) -> Path:
    """
    Store the file in a unique subfolder under output/ and return the relative path to the file.
    """
    # Create a unique folder name inside the output directory
    unique_folder = OUTPUT_DIR / str(uuid.uuid4())
    unique_folder.mkdir(parents=True, exist_ok=True)

    # Copy the input file to the unique folder
    target_file = unique_folder / input_path.name
    shutil.copy(input_path, target_file)

    # Return the relative path: output/<unique folder>/<file name>
    return target_file.relative_to(OUTPUT_DIR.parent)
