import os
import shutil

def secure_path(base_dir, target_name):
    """Ensure the target path resolves strictly within the base directory to prevent accidental overwrites."""
    abs_base = os.path.abspath(base_dir)
    target_path = os.path.abspath(os.path.join(base_dir, target_name))
    if not target_path.startswith(abs_base):
        raise Exception(f"Security constraint violated: '{target_name}' attempts to break out of {base_dir}")
    return target_path

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def create_folder(directory, foldername):
    ensure_dir(directory)
    folder_path = secure_path(directory, foldername)
    ensure_dir(folder_path)
    return f"Successfully created folder: {folder_path}"

def create_file(directory, filename, content=""):
    ensure_dir(directory)
    filepath = secure_path(directory, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Successfully created file: {filepath}"

def write_code(directory, filename, code):
    ensure_dir(directory)
    filepath = secure_path(directory, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)
    return f"Successfully wrote code to: {filepath}"

def list_files(directory):
    ensure_dir(directory)
    return os.listdir(directory)
