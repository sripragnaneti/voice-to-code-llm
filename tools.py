import os
import shutil
import ast
import subprocess
import tempfile

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

def verify_code(filepath):
    """Verifies syntax for Python, Java, and C/C++."""
    if not os.path.exists(filepath):
        return False, "File does not exist."
        
    ext = os.path.splitext(filepath)[1].lower()
    
    if ext == ".py":
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                ast.parse(f.read())
            return True, "Python Syntax: Valid ✅"
        except SyntaxError as e:
            return False, f"Python Syntax Error: {e.msg} at line {e.lineno}"
        except Exception as e:
            return False, f"Error: {str(e)}"
            
    elif ext == ".java":
        if not shutil.which("javac"):
            return None, "JDK (javac) not found on system. Cannot verify Java syntax."
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                res = subprocess.run(["javac", "-d", tmpdir, filepath], capture_output=True, text=True)
                if res.returncode == 0:
                    return True, "Java Syntax: Valid ✅"
                else:
                    return False, f"Java Syntax Error:\n{res.stderr}"
        except Exception as e:
            return False, f"Process Error: {str(e)}"

    elif ext in [".c", ".cpp"]:
        compiler = "gcc" if ext == ".c" else "g++"
        if not shutil.which(compiler):
            return None, f"Compiler ({compiler}) not found on system. Cannot verify C syntax."
        try:
            res = subprocess.run([compiler, "-fsyntax-only", filepath], capture_output=True, text=True)
            if res.returncode == 0:
                return True, f"{ext.upper()[1:]} Syntax: Valid ✅"
            else:
                return False, f"{ext.upper()[1:]} Syntax Error:\n{res.stderr}"
        except Exception as e:
            return False, f"Process Error: {str(e)}"

    return None, f"Syntax verification not supported for {ext} files."
