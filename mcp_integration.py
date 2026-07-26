# [Vikalp Sharma] - Proprietary / Anti-Theft Watermark
import os
import shutil
import json
import subprocess
import threading
import time


class MCPClient:
    """Client for connecting to external MCP servers via JSON-RPC over stdio."""

    def __init__(self, name, command, args=None, env=None):
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.process = None
        self.tools = []
        self._lock = threading.Lock()
        self._request_id = 0
        self._connected = False

    def connect(self, timeout=10):
        """Start the MCP server subprocess and initialize the connection."""
        try:
            full_env = os.environ.copy()
            full_env.update(self.env)
            cmd = [self.command] + self.args
            self.process = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, env=full_env,
                bufsize=0, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            )
            # Send initialize request
            init_result = self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "DarkMaxxer", "version": "2.5.0"}
            }, timeout=timeout)
            if init_result is not None:
                # Send initialized notification
                self._send_notification("notifications/initialized", {})
                self._connected = True
                # Discover tools
                self._discover_tools()
                return True
            return False
        except Exception as e:
            self._connected = False
            return False

    def _discover_tools(self):
        """Fetch available tools from the MCP server."""
        try:
            result = self._send_request("tools/list", {})
            if result and "tools" in result:
                self.tools = result["tools"]
            elif isinstance(result, list):
                self.tools = result
        except Exception:
            self.tools = []

    def call_tool(self, tool_name, arguments=None):
        """Call a tool on the MCP server."""
        if not self._connected or not self.process:
            return {"error": f"MCP server '{self.name}' is not connected"}
        try:
            result = self._send_request("tools/call", {
                "name": tool_name,
                "arguments": arguments or {}
            }, timeout=30)
            if result and "content" in result:
                # Extract text from content array
                texts = []
                for item in result["content"]:
                    if isinstance(item, dict) and item.get("type") == "text":
                        texts.append(item.get("text", ""))
                    elif isinstance(item, str):
                        texts.append(item)
                return {"success": True, "result": "\n".join(texts) if texts else str(result)}
            return {"success": True, "result": str(result) if result else "OK"}
        except Exception as e:
            return {"error": str(e)}

    def _send_request(self, method, params, timeout=15):
        """Send a JSON-RPC request and wait for the response."""
        with self._lock:
            self._request_id += 1
            req_id = self._request_id
            msg = json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "method": method,
                "params": params
            }) + "\n"
            try:
                self.process.stdin.write(msg.encode("utf-8"))
                self.process.stdin.flush()
            except (BrokenPipeError, OSError):
                self._connected = False
                return None

            # Read response with timeout
            deadline = time.time() + timeout
            buffer = ""
            while time.time() < deadline:
                if self.process.poll() is not None:
                    self._connected = False
                    return None
                try:
                    self.process.stdout.settimeout = timeout
                    line = self.process.stdout.readline()
                    if not line:
                        time.sleep(0.05)
                        continue
                    buffer += line.decode("utf-8", errors="replace")
                    # Try to parse each complete line
                    for json_line in buffer.strip().split("\n"):
                        json_line = json_line.strip()
                        if not json_line:
                            continue
                        try:
                            resp = json.loads(json_line)
                            if resp.get("id") == req_id:
                                if "error" in resp:
                                    return None
                                return resp.get("result")
                        except json.JSONDecodeError:
                            continue
                    buffer = ""
                except Exception:
                    time.sleep(0.05)
            return None

    def _send_notification(self, method, params):
        """Send a JSON-RPC notification (no response expected)."""
        msg = json.dumps({
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }) + "\n"
        try:
            self.process.stdin.write(msg.encode("utf-8"))
            self.process.stdin.flush()
        except Exception:
            pass

    def disconnect(self):
        """Terminate the MCP server subprocess."""
        self._connected = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

    def get_tool_descriptions(self):
        """Return a formatted string of available tools for injection into the system prompt."""
        if not self.tools:
            return ""
        lines = [f"MCP Server: {self.name}"]
        for tool in self.tools:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "No description")
            schema = tool.get("inputSchema", {})
            props = schema.get("properties", {})
            param_strs = []
            for pname, pinfo in props.items():
                ptype = pinfo.get("type", "any")
                param_strs.append(f"{pname}: {ptype}")
            params = ", ".join(param_strs) if param_strs else "none"
            lines.append(f"  - {name}({params}): {desc}")
        return "\n".join(lines)

    @property
    def is_connected(self):
        return self._connected and self.process and self.process.poll() is None


class FileOpsServer:
    """Local file operations server for workspace management."""

    def __init__(self, base_dir: str):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def _safe_path(self, rel_path: str) -> str:
        """Resolve a relative path safely within the base directory."""
        full = os.path.normpath(os.path.join(self.base_dir, rel_path))
        if not full.startswith(self.base_dir):
            raise ValueError(f"Path traversal blocked: '{rel_path}' escapes workspace.")
        return full

    # --- File Operations ---

    def list_files(self, sub_dir: str = "") -> list:
        """List files in the workspace (or a subdirectory)."""
        target = self._safe_path(sub_dir) if sub_dir else self.base_dir
        if not os.path.isdir(target):
            return []
        result = []
        for name in os.listdir(target):
            full = os.path.join(target, name)
            if os.path.isfile(full):
                result.append({"name": name, "size": os.path.getsize(full)})
        return result

    def list_folders(self, sub_dir: str = "") -> list:
        """List subdirectories in the workspace."""
        target = self._safe_path(sub_dir) if sub_dir else self.base_dir
        if not os.path.isdir(target):
            return []
        result = []
        for name in os.listdir(target):
            full = os.path.join(target, name)
            if os.path.isdir(full):
                result.append({"name": name})
        return result

    def list_tree_recursive(self, max_depth=10):
        """Recursively walk workspace and return flat relative paths for files and folders.
        Skips hidden directories, build artifacts, and large dependency dirs."""
        skip_dirs = {'.git', '__pycache__', 'node_modules', 'venv', '.venv', 
                     'build', 'dist', '.idea', '.vscode', '.mypy_cache',
                     '.pytest_cache', 'egg-info', '.eggs', '.tox'}
        files = []
        folders = []

        def _walk(current_dir, rel_prefix, depth):
            if depth > max_depth:
                return
            try:
                entries = sorted(os.listdir(current_dir))
            except PermissionError:
                return
            for name in entries:
                if name.startswith('.') and name not in ('.env',):
                    continue
                full = os.path.join(current_dir, name)
                rel = (rel_prefix + '/' + name) if rel_prefix else name
                if os.path.isdir(full):
                    base_lower = name.lower()
                    if base_lower in skip_dirs or base_lower.endswith('.egg-info'):
                        continue
                    folders.append(rel)
                    _walk(full, rel, depth + 1)
                elif os.path.isfile(full):
                    files.append(rel)

        _walk(self.base_dir, '', 0)
        return {"files": files, "folders": folders}

    def read_file(self, rel_path: str) -> str:
        """Read a file's contents."""
        full = self._safe_path(rel_path)
        if not os.path.isfile(full):
            raise FileNotFoundError(f"File not found: '{rel_path}'")
        with open(full, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def create_file(self, rel_path: str, content: str = "") -> dict:
        """Create a new file."""
        full = self._safe_path(rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "path": rel_path}

    def create_directory(self, rel_path: str) -> dict:
        """Create a new directory."""
        full = self._safe_path(rel_path)
        os.makedirs(full, exist_ok=True)
        return {"success": True, "path": rel_path}

    def edit_file(self, rel_path: str, content: str) -> dict:
        """Overwrite a file with new content."""
        full = self._safe_path(rel_path)
        if not os.path.isfile(full):
            raise FileNotFoundError(f"File not found: '{rel_path}'")
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "path": rel_path}

    def append_file(self, rel_path: str, content: str) -> dict:
        """Append content to an existing file."""
        full = self._safe_path(rel_path)
        if not os.path.isfile(full):
            raise FileNotFoundError(f"File not found: '{rel_path}'")
        with open(full, "a", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "path": rel_path}

    def delete_file(self, rel_path: str) -> dict:
        """Delete a file."""
        full = self._safe_path(rel_path)
        if not os.path.exists(full):
            raise FileNotFoundError(f"File not found: '{rel_path}'")
        if os.path.isfile(full):
            os.remove(full)
        elif os.path.isdir(full):
            shutil.rmtree(full)
        return {"success": True, "path": rel_path}

    def rename_file(self, old_path: str, new_path: str) -> dict:
        """Rename / move a file within the workspace."""
        old_full = self._safe_path(old_path)
        new_full = self._safe_path(new_path)
        if not os.path.exists(old_full):
            raise FileNotFoundError(f"Source not found: '{old_path}'")
        os.makedirs(os.path.dirname(new_full), exist_ok=True)
        os.rename(old_full, new_full)
        return {"success": True, "old": old_path, "new": new_path}
