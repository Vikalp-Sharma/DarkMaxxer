# [Vikalp Sharma] - Proprietary / Anti-Theft Watermark
import os

# Vikalp Sharma
# Proprietary License - Do not redistribute without permission.

class FileOpsServer:
    def __init__(self, base_dir: str):
        self.base_dir = os.path.realpath(os.path.abspath(base_dir))

    def _get_safe_path(self, relative_path: str) -> str:
        """Ensure the path is strictly within the base_dir to prevent directory traversal or symlink escape."""
        clean_rel = relative_path.lstrip('/\\') if relative_path else "."
        if not clean_rel:
            clean_rel = "."
        full_path = os.path.realpath(os.path.abspath(os.path.join(self.base_dir, clean_rel)))
        try:
            if os.path.commonpath([self.base_dir, full_path]) != self.base_dir:
                raise ValueError(f"Security Alert: Path traversal denied. '{relative_path}' is outside workspace folder '{self.base_dir}'. Nothing can escape the workspace folder.")
        except ValueError as e:
            if "Security Alert" in str(e):
                raise e
            raise ValueError("Security Alert: Path traversal denied across drives or boundaries. Nothing can escape the workspace folder.")
        return full_path

    def create_file(self, relative_path: str, content: str) -> str:
        """Create a new file or overwrite an existing file with the given content."""
        full_path = self._get_safe_path(relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully created/overwritten {relative_path}"

    def edit_file(self, relative_path: str, content: str) -> str:
        """Edit an existing file or create it if missing, replacing its content."""
        full_path = self._get_safe_path(relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully edited/created {relative_path}"

    def delete_file(self, relative_path: str) -> str:
        """Delete a file."""
        full_path = self._get_safe_path(relative_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File {relative_path} does not exist.")
            
        os.remove(full_path)
        return f"Successfully deleted {relative_path}"

    def read_file(self, relative_path: str) -> str:
        """Read a file's content."""
        full_path = self._get_safe_path(relative_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"File {relative_path} does not exist.")
            
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()

    def list_files(self, relative_path: str = ".") -> list:
        """List files in the workspace directory."""
        full_path = self._get_safe_path(relative_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Directory {relative_path} does not exist.")
        
        tree = []
        for root, dirs, files in os.walk(full_path):
            dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__', 'node_modules', '.gemini', '.system_generated', 'venv', 'dist', 'build')]
            for file in files:
                rel_p = os.path.relpath(os.path.join(root, file), self.base_dir).replace('\\', '/')
                tree.append(rel_p)
                if len(tree) >= 2000:
                    return sorted(tree)
        return sorted(tree)

    def list_folders(self, relative_path: str = ".") -> list:
        """List directories in the workspace directory."""
        full_path = self._get_safe_path(relative_path)
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Directory {relative_path} does not exist.")
        
        folders = []
        for root, dirs, files in os.walk(full_path):
            dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__', 'node_modules', '.gemini', '.system_generated', 'venv', 'dist', 'build')]
            for d in dirs:
                rel_d = os.path.relpath(os.path.join(root, d), self.base_dir).replace('\\', '/')
                folders.append(rel_d)
                if len(folders) >= 2000:
                    return sorted(folders)
        return sorted(folders)

