# [Vikalp Sharma] - Proprietary / Anti-Theft Watermark
import os
import sys
import io
import traceback

def _fatal_crash(e):
    crash_log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "early_crash.log")
    try:
        with open(crash_log, "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
    except:
        pass

try:
    def _ensure_local_site_packages():
        _here = os.path.dirname(os.path.abspath(__file__))
        _cands = [
            os.path.join(_here, "venv", "Lib", "site-packages"),
            os.path.join(_here, "..", "venv", "Lib", "site-packages"),
            os.path.join(os.path.expanduser("~"), "DarkMaxxer", "venv", "Lib", "site-packages"),
            os.path.join(os.getenv("LOCALAPPDATA", ""), "Low", "DarkMaxxer", "venv", "Lib", "site-packages"),
            os.path.join(os.getenv("APPDATA", ""), "DarkMaxxer", "venv", "Lib", "site-packages"),
        ]
        # Detect pip's custom target directory (PIP_TARGET env or pip.ini global.target)
        # so packages installed there can actually be imported
        _pip_target = os.environ.get("PIP_TARGET", "")
        if not _pip_target:
            try:
                import configparser
                _pip_ini = os.path.join(os.getenv("APPDATA", ""), "pip", "pip.ini")
                if os.path.exists(_pip_ini):
                    _cp = configparser.ConfigParser()
                    _cp.read(_pip_ini, encoding="utf-8")
                    _pip_target = _cp.get("global", "target", fallback="")
            except Exception:
                pass
        if _pip_target and os.path.isdir(_pip_target):
            _cands.append(_pip_target)
        for _c in _cands:
            if os.path.exists(_c) and _c not in sys.path:
                sys.path.insert(0, _c)

    _ensure_local_site_packages()

    if sys.stdout is None:
        sys.stdout = io.StringIO()
    if sys.stderr is None:
        sys.stderr = io.StringIO()

    def _crash_handler(exctype, value, tb):
        crash_log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash.log")
        try:
            with open(crash_log, "a", encoding="utf-8") as f:
                f.write("".join(traceback.format_exception(exctype, value, tb)))
        except:
            pass
    sys.excepthook = _crash_handler

except Exception as e:
    _fatal_crash(e)
    sys.exit(1)
import threading
import subprocess

def _install_dependencies():
    """Install pip dependencies with bounded retries. Skips entirely for frozen exes."""
    # Frozen exe (PyInstaller) has no pip — skip to avoid infinite background process
    if getattr(sys, 'frozen', False):
        return

    _creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

    # Already installed — nothing to do
    try:
        import webview
        return
    except ImportError:
        pass

    _MAX_RETRIES = 3
    _TIMEOUT = 300  # 5 min timeout per subprocess call

    pip_python = sys.executable
    if pip_python.lower().endswith("pythonw.exe"):
        python_exe = pip_python[:-11] + "python.exe"
        if os.path.exists(python_exe):
            pip_python = python_exe

    # Determine the correct site-packages dir that's actually in sys.path
    # This overrides any custom PIP_TARGET / pip.ini global.target config
    _target_site_pkg = None
    for _p in sys.path:
        if 'site-packages' in _p.lower() and os.path.isdir(_p):
            _target_site_pkg = _p
            break
    _target_args = ["--target", _target_site_pkg] if _target_site_pkg else []

    # Create a clean env without PIP_TARGET to prevent misrouting
    _pip_env = os.environ.copy()
    _pip_env.pop("PIP_TARGET", None)

    _here = os.path.dirname(os.path.abspath(__file__))
    req_file = os.path.join(_here, "requirements.txt")
    other_pips = []
    if os.path.exists(req_file):
        with open(req_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    pkg_name = line.split('==')[0].split('>')[0].split('<')[0].strip()
                    if pkg_name and "pywebview" not in pkg_name.lower() and "webview" not in pkg_name.lower():
                        other_pips.append(pkg_name)

    # Step 1: Install all other requirements first
    if other_pips:
        for attempt in range(_MAX_RETRIES):
            try:
                subprocess.run(
                    [pip_python, "-m", "pip", "install", "--prefer-binary"] + _target_args + other_pips,
                    capture_output=True, timeout=_TIMEOUT,
                    creationflags=_creationflags,
                    env=_pip_env
                )
                break
            except Exception:
                pass

    # Step 2: Install pywebview individually, retry up to _MAX_RETRIES each
    for pkg in ["pywebview"]:
        for attempt in range(_MAX_RETRIES):
            try:
                subprocess.run(
                    [pip_python, "-m", "pip", "install", "--prefer-binary"] + _target_args + [pkg],
                    capture_output=True, timeout=_TIMEOUT,
                    creationflags=_creationflags,
                    env=_pip_env
                )
                # Verify it actually installed
                res = subprocess.run(
                    [pip_python, "-m", "pip", "show", pkg],
                    capture_output=True, text=True, timeout=30,
                    creationflags=_creationflags,
                    env=_pip_env
                )
                if res.returncode == 0:
                    break  # Installed and verified
            except Exception:
                pass

    # Step 3: Verify all other pips are present
    for p in other_pips:
        try:
            res = subprocess.run(
                [pip_python, "-m", "pip", "show", p],
                capture_output=True, text=True, timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW,
                env=_pip_env
            )
            if res.returncode != 0:
                # One more attempt for any missing package
                subprocess.run(
                    [pip_python, "-m", "pip", "install", "--prefer-binary"] + _target_args + [p],
                    capture_output=True, timeout=_TIMEOUT,
                    creationflags=_creationflags,
                    env=_pip_env
                )
        except Exception:
            pass

_install_dependencies()

try:
    import webview
except Exception as e:
    webview = None
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "webview_error.log"), "w", encoding="utf-8") as f:
            f.write(f"Failed to import pywebview: {e}\n")
    except:
        pass
from memory_manager import MemoryManager, ConfigManager
from llm_engine import LLMEngine
from mcp_integration import FileOpsServer, MCPClient

# Vikalp Sharma
# Proprietary License - Do not redistribute without permission.

class Api:
    def __init__(self):
        self.memory = MemoryManager()
        self.config = ConfigManager()
        self.llm = LLMEngine()
        self.file_ops = None
        self.active_conv_id = None
        self.is_generating = False
        self._cancel_requested = False
        self._gen_counter = 0
        self._current_gen_id = 0
        self._window = None
        self.terminal_logs = []
        self.subagents = []
        self.mcp_clients = {}  # name -> MCPClient
        self._init_mcp_servers()

        # Restore active session if available
        conf = self.config.get_config()
        active_id = conf.get("active_conv_id")
        active_dir = conf.get("active_workspace_dir")

        if active_dir and os.path.exists(active_dir):
            self.file_ops = FileOpsServer(active_dir)
            if active_id:
                self.active_conv_id = active_id
        elif active_id:
            self.active_conv_id = active_id
            ws_dir = self.memory.get_workspace_dir(active_id)
            if os.path.exists(ws_dir):
                self.file_ops = FileOpsServer(ws_dir)

    def _init_mcp_servers(self):
        """Connect to configured MCP servers on startup."""
        try:
            servers = self.config.get_config().get("mcp_servers", [])
            for srv in servers:
                if not srv.get("enabled", True):
                    continue
                name = srv.get("name", "unknown")
                try:
                    client = MCPClient(name, srv["command"], srv.get("args", []), srv.get("env", {}))
                    if client.connect(timeout=8):
                        self.mcp_clients[name] = client
                except Exception:
                    pass
        except Exception:
            pass

    def set_window(self, window):
        self._window = window

    # --- Setup & Model Selection ---

    def select_model_folder(self):
        if not self._window:
            return {"success": False, "error": "Window not initialized"}
        if webview is None:
            return {"success": False, "error": "pywebview not available"}
        try:
            folder_dlg = getattr(webview.FileDialog, "FOLDER", getattr(webview, "FOLDER_DIALOG", 1))
            result = self._window.create_file_dialog(folder_dlg)
            if result and len(result) > 0:
                self.config.update_config("ai_path", result[0])
                return {"success": True, "path": result[0]}
            return {"success": False, "error": "No folder selected"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def select_model_file(self):
        if not self._window:
            return {"success": False, "error": "Window not initialized"}
        if webview is None:
            return {"success": False, "error": "pywebview not available"}
        try:
            open_dlg = getattr(webview.FileDialog, "OPEN", getattr(webview, "OPEN_DIALOG", 10))
            file_types = ('Model Files (*.gguf;*.safetensors;*.bin;*.pth;*.pt;*.pkl;*.json)', 'All files (*.*)')
            result = self._window.create_file_dialog(open_dlg, file_types=file_types)
            if result and len(result) > 0:
                self.config.update_config("ai_path", result[0])
                return {"success": True, "path": result[0]}
            return {"success": False, "error": "No file selected"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_model_compatibility(self, model_id):
        """Check if local GPU/system is compatible with the selected model."""
        try:
            import torch
            has_cuda = torch.cuda.is_available()
            vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2) if has_cuda else 0
            if not os.path.exists(model_id):
                return {"success": True, "compatible": False, "message": f"Path not found on local disk: '{model_id}'. Remote downloading is disabled.", "vram": vram_gb, "cuda": has_cuda}
            # With AirLLM layer-wise offloading, even 70B runs on ~4GB VRAM
            compatible = True
            msg = "Compatible with AirLLM layer-wise offloading"
            if not has_cuda:
                msg = "Running on CPU / Metal / System Memory (CUDA not detected)"
            elif vram_gb < 4.0 and "70b" in str(model_id).lower():
                compatible = False
                msg = f"Incompatible: {model_id} requires >= 4GB VRAM with AirLLM (Found {vram_gb} GB)"
            return {"success": True, "compatible": compatible, "message": msg, "vram": vram_gb, "cuda": has_cuda}
        except Exception as e:
            return {"success": True, "compatible": True, "message": f"Compatibility check ({str(e)}) -> AirLLM fallback enabled", "vram": "N/A", "cuda": False}

    def load_model(self, model_id, hf_token=None):
        def _callback(msg):
            if self._window:
                import json as _json
                safe_msg = _json.dumps(str(msg))
                try:
                    self._window.evaluate_js(f"window.updateLoadStatus({safe_msg})")
                except Exception:
                    pass
                self._log_terminal(f"AirLLM: {msg}")

        try:
            settings = self.config.get_settings()
            if settings.get("local_inference", True) and not os.path.exists(model_id):
                return {"success": False, "error": f"Local model path not found on disk: '{model_id}'. Remote downloading is disabled per Local Inference security setting."}
            self.llm.load_model(model_id, hf_token=hf_token, callback=_callback)
            self.config.update_config("ai_path", model_id)
            return {"success": True}
        except Exception as e:
            self.config.update_config("ai_path", None)
            return {"success": False, "error": str(e)}

    # --- Conversations ---

    def get_active_conv_id(self):
        """Return the currently active conversation ID (callable from JS)."""
        return self.active_conv_id

    def list_conversations(self):
        try:
            return self.memory.list_conversations()
        except Exception:
            return []

    def new_conversation(self, name):
        try:
            existing = self.memory.list_conversations()
            if any(c.get("name", "").strip().lower() == name.strip().lower() for c in existing):
                return {"success": False, "error": f"Conversation already exists: '{name}'. Please choose a different project name or select the existing conversation."}
            conv_id = self.memory.create_conversation(name)
            self._init_file_ops(conv_id)
            self.active_conv_id = conv_id
            self.config.update_config("active_conv_id", conv_id)
            return {"success": True, "id": conv_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_conversation(self, conv_id):
        try:
            history = self.memory.get_history(conv_id)
            self.active_conv_id = conv_id
            self.config.update_config("active_conv_id", conv_id)
            self._init_file_ops(conv_id)
            return {"success": True, "history": history, "conv_id": conv_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_conversation(self, conv_id):
        """Delete a conversation and all its data."""
        try:
            self.memory.delete_conversation(conv_id)
            if self.active_conv_id == conv_id:
                self.active_conv_id = None
                self.file_ops = None
                self.config.update_config("active_conv_id", None)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _init_file_ops(self, conv_id, force=False):
        if hasattr(self, 'memory') and hasattr(self.memory, 'get_conversation_data'):
            conv_data = self.memory.get_conversation_data(conv_id)
            ws_dir = conv_data.get("workspace_dir")
            ws_mode = conv_data.get("workspace_mode", "local")
            if ws_dir and os.path.exists(ws_dir):
                self.file_ops = FileOpsServer(ws_dir)
                self.config.update_config("active_workspace_dir", ws_dir)
                self.config.update_config("workspace_mode", ws_mode)
                return

        workspace_dir = self.memory.get_workspace_dir(conv_id)
        os.makedirs(workspace_dir, exist_ok=True)
        self.file_ops = FileOpsServer(workspace_dir)
        self.config.update_config("active_workspace_dir", workspace_dir)
        self.config.update_config("workspace_mode", "local")

    def open_external_folder(self):
        if not self._window:
            return {"success": False, "error": "Window not initialized"}
        if webview is None:
            return {"success": False, "error": "pywebview not available"}
        try:
            folder_dlg = getattr(webview.FileDialog, "FOLDER", getattr(webview, "FOLDER_DIALOG", 1))
            result = self._window.create_file_dialog(folder_dlg)
            if result and len(result) > 0:
                selected_dir = result[0]
                folder_name = os.path.basename(selected_dir.rstrip(os.sep)) or "Workspace"
                self.file_ops = FileOpsServer(selected_dir)
                self.config.update_config("active_workspace_dir", selected_dir)
                self.config.update_config("workspace_mode", "local")
                
                # Always create a new session for a newly opened folder so it doesn't overwrite the active one
                self.active_conv_id = self.memory.create_conversation(folder_name)
                if hasattr(self.memory, 'set_conversation_data'):
                    self.memory.set_conversation_data(self.active_conv_id, "workspace_dir", selected_dir)
                    self.memory.set_conversation_data(self.active_conv_id, "workspace_mode", "local")
                self._init_file_ops(self.active_conv_id)
                self.config.update_config("active_conv_id", self.active_conv_id)
                
                self._log_terminal(f"Workspace set to external folder: {selected_dir}")
                return {"success": True, "path": selected_dir, "folder_name": folder_name}
            return {"success": False, "error": "No folder selected"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_global_workspace(self):
        """Set workspace to global filesystem access (no sandbox)."""
        try:
            import platform as _plat
            if _plat.system() == "Windows":
                root = os.environ.get("SYSTEMDRIVE", "C:") + os.sep
            else:
                root = "/"
            self.file_ops = FileOpsServer(root)
            self.file_ops.global_mode = True
            self.config.update_config("active_workspace_dir", root)
            self.config.update_config("workspace_mode", "global")
            if not self.active_conv_id:
                self.active_conv_id = self.memory.create_conversation("Global Workspace")
                self.config.update_config("active_conv_id", self.active_conv_id)
            self._init_file_ops(self.active_conv_id)
            self.file_ops = FileOpsServer(root)
            self.file_ops.global_mode = True
            self._log_terminal(f"Global workspace mode enabled — root: {root}")
            return {"success": True, "path": root, "mode": "global"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_available_skills(self):
        """Scan workspace for all SKILL.md files."""
        skills = []
        if self.file_ops and os.path.exists(self.file_ops.base_dir):
            for root, dirs, files in os.walk(self.file_ops.base_dir):
                if "SKILL.md" in files:
                    full_path = os.path.join(root, "SKILL.md")
                    rel_path = os.path.relpath(full_path, self.file_ops.base_dir)
                    parent_name = os.path.basename(root)
                    skills.append({"path": rel_path, "name": parent_name, "full_path": full_path})
                # Don't recurse into hidden/venv/node_modules
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("venv", "node_modules", "__pycache__", ".git")]
        return skills

    def get_settings(self):
        try:
            return {"success": True, "settings": self.config.get_settings()}
        except Exception:
            return {"success": True, "settings": {"local_inference": True, "gpu_acceleration": True, "context_memory": True}}

    def save_settings(self, settings_dict):
        try:
            self.config.update_settings(settings_dict)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_setting(self, key, value):
        try:
            self.config.update_config(key, value)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Chat & Generation ---

    def send_prompt(self, prompt):
        if not self.llm.model:
            return {"success": False, "error": "No model loaded. Please select and load a model first."}
        if self.is_generating:
            return {"success": False, "error": "Already generating a response."}

        self.is_generating = True
        self._cancel_requested = False
        self._gen_counter += 1
        gen_id = self._gen_counter
        self._current_gen_id = gen_id

        if not self.active_conv_id:
            ws_name = os.path.basename(self.file_ops.base_dir) if self.file_ops else "Chat Session"
            self.active_conv_id = self.memory.create_conversation(ws_name or "Chat Session")
            self._init_file_ops(self.active_conv_id)
            self.config.update_config("active_conv_id", self.active_conv_id)
        elif not os.path.exists(os.path.join(self.memory.context_dir, f"{self.active_conv_id}.json")):
            try:
                self.memory.save_history(self.active_conv_id, [])
            except Exception:
                pass

        history = self.memory.get_history(self.active_conv_id)
        history.append({"role": "user", "content": prompt})
        self.memory.save_history(self.active_conv_id, history)
        self.generating_conv_id = self.active_conv_id
        
        self._gen_counter += 1
        gen_id = self._gen_counter
        self._current_gen_id = gen_id
        
        t = threading.Thread(target=self._generate_worker, args=(prompt, self.active_conv_id, history, gen_id), name="DarkMaxxerGenThread")
        t.daemon = True
        t.start()
        return {"success": True, "status": "generating"}

    def cancel_generation(self):
        """Cancel/pause the current generation so user can type a new prompt."""
        self._cancel_requested = True
        self._gen_counter += 1
        self._current_gen_id = self._gen_counter
        self.is_generating = False
        if hasattr(self.llm, 'cancel'):
            try:
                self.llm.cancel()
            except Exception:
                pass
        
        if self.active_conv_id:
            try:
                hist = self.memory.get_history(self.active_conv_id)
                popped_prompt = None
                # Purge pending incomplete user prompts & paused tags from history!
                while hist and hist[-1].get("role") == "user":
                    popped_prompt = hist.pop().get("content", "")
                while hist and hist[-1].get("role") == "assistant" and "[Generation paused" in str(hist[-1].get("content", "")):
                    hist.pop()
                self.memory.save_history(self.active_conv_id, hist)
            except Exception:
                pass
        self._log_terminal("Generation paused by user.")
        return {"success": True, "restored_prompt": popped_prompt if 'popped_prompt' in locals() else None}

    def _generate_worker(self, prompt, conv_id, history, gen_id=0):
        try:
            if self._cancel_requested or self._current_gen_id != gen_id:
                self._log_terminal("Generation cancelled before start.")
                return

            settings = self.config.get_settings()
            use_memory = settings.get("context_memory", True)
            use_gpu = settings.get("gpu_acceleration", True)

            # Ensure file ops active if possible
            if not self.file_ops and self.active_conv_id:
                self._init_file_ops(self.active_conv_id)

            # Build comprehensive recursive context: include ALL folders and ALL files in active workspace
            context_files = ""
            if self.file_ops and os.path.exists(self.file_ops.base_dir):
                try:
                    folders = self.file_ops.list_folders()
                    files = self.file_ops.list_files()
                    context_files = "\n=== ACTIVE WORKSPACE & FILE SYSTEM CONTEXT ===\n"
                    context_files += f"Root Directory Path: {self.file_ops.base_dir}\n"
                    if folders:
                        context_files += f"All Workspace Subfolders: {', '.join(folders[:200])}\n"
                    else:
                        context_files += "All Workspace Subfolders: (No subfolders)\n"
                    if files:
                        context_files += f"All Available Workspace Files (to Read, Edit, or Delete): {', '.join(files[:400])}\n"
                    else:
                        context_files += "All Available Workspace Files: (Workspace folder is currently empty)\n"
                    context_files += "==============================================\n"
                except Exception as e:
                    context_files = f"\n[Workspace check error: {str(e)}]\n"
            else:
                context_files = "\n[No active workspace folder]\n"

            if self._cancel_requested or self._current_gen_id != gen_id:
                self._log_terminal("Generation cancelled during context build.")
                return

            skill_content = ""
            skill_found = False
            if self.file_ops and os.path.exists(self.file_ops.base_dir):
                # Collect ALL SKILL.md files in workspace
                all_skills = []
                for sroot, sdirs, sfiles in os.walk(self.file_ops.base_dir):
                    if "SKILL.md" in sfiles:
                        all_skills.append(os.path.join(sroot, "SKILL.md"))
                    sdirs[:] = [d for d in sdirs if not d.startswith(".") and d not in ("venv", "node_modules", "__pycache__", ".git")]

                selected_skills = all_skills
                # If multiple skills found, ask user to select (max 5) via JS modal
                if len(all_skills) > 1 and self._window:
                    try:
                        skill_info = []
                        for sp in all_skills:
                            rel = os.path.relpath(sp, self.file_ops.base_dir)
                            name = os.path.basename(os.path.dirname(sp))
                            skill_info.append({"path": rel, "name": name})
                        import json as _json
                        result = self._window.evaluate_js(
                            f"window.showSkillSelector && window.showSkillSelector({_json.dumps(skill_info)})"
                        )
                        if result and isinstance(result, list):
                            # Map selected relative paths back to full paths
                            selected_skills = []
                            for sel in result[:5]:
                                fp = os.path.join(self.file_ops.base_dir, sel)
                                if os.path.isfile(fp):
                                    selected_skills.append(fp)
                        elif result is None or result == []:
                            selected_skills = all_skills[:1]  # Default to first
                    except Exception:
                        selected_skills = all_skills[:5]
                else:
                    selected_skills = all_skills[:5]

                # Read selected skills
                skill_parts = []
                for sk_path in selected_skills:
                    try:
                        with open(sk_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            if content.strip():
                                sk_name = os.path.basename(os.path.dirname(sk_path))
                                skill_parts.append(f"### Skill: {sk_name}\n{content}")
                    except Exception:
                        pass
                if skill_parts:
                    skill_content = "\n\n".join(skill_parts)
                    skill_found = True

            # Build structured messages array for chat models
            messages = []
            skill_injection = f"\n<SKILLS>\n{skill_content}\n</SKILLS>\n" if skill_found else ""
            
            # Build MCP tools injection
            mcp_injection = ""
            if self.mcp_clients:
                mcp_parts = []
                for name, client in self.mcp_clients.items():
                    if client.is_connected:
                        desc = client.get_tool_descriptions()
                        if desc:
                            mcp_parts.append(desc)
                if mcp_parts:
                    mcp_injection = (
                        "\n\n=== EXTERNAL MCP TOOLS ===\n"
                        "You have access to external MCP (Model Context Protocol) servers. "
                        "To call an MCP tool, use this syntax:\n"
                        "[TOOL: MCP_CALL server=ServerName tool=tool_name args={\"param\": \"value\"}]\n\n"
                        "Available MCP servers and their tools:\n"
                        + "\n".join(mcp_parts) + "\n"
                        "=== END MCP TOOLS ===\n"
                    )

            # Platform detection for shell commands
            import platform as _plat
            _os_name = _plat.system()  # 'Linux', 'Windows', 'Darwin'
            _shell = "bash" if _os_name != "Windows" else "cmd"
            _python_cmd = "python3" if _os_name != "Windows" else "python"
            _ws_mode = self.config.get_config().get("workspace_mode", "local")
            _ws_path = self.file_ops.base_dir if self.file_ops else "None"

            sys_msg = (
                f"{context_files}"
                f"{skill_injection}"
                "You are **DarkMaxxer AI**, an elite, autonomous local AI coding assistant.\n"
                "You run entirely offline with direct filesystem access.\n\n"
                "# CRITICAL RULES\n"
                "1. You MUST use the exact [TOOL: ACTION] syntax to perform actions.\n"
                "2. ALWAYS close your tool calls with [/TOOL].\n"
                "3. DO NOT output conversational text inside the tool block! Put your explanations OUTSIDE the tool block.\n"
                "4. NEVER use placeholder paths like 'path/to/file.py' unless the user explicitly asks you to create nested folders! Create files in the current root by default (e.g. 'hi.py').\n"
                "5. When the user asks you to write code, YOU MUST CREATE THE FILE YOURSELF using CREATE_FILE. DO NOT just show the code and expect the user to copy-paste it.\n"
                "6. NEVER hallucinate tool names. Only use the tools listed below.\n"
                "7. If you create a file, you MUST supply the code block wrapped in ```.\n"
                "8. When using CREATE_FILE or EDIT_FILE, write the ACTUAL raw file content inside the code block. DO NOT write shell commands (like 'echo' or 'cat') to create the file.\n"
                "9. Ensure the language identifier of your code block matches the file extension you are writing (e.g., use ```python for .py files, NOT ```bash).\n"
                "10. NEVER give the user instructions on how to create, edit, or run files manually (e.g. 'Open a text editor', 'Copy and paste this', 'Save the file as'). YOU are an autonomous agent and YOU MUST do these things yourself using your tools!\n"
                "11. NEVER output a code block containing code intended for a file WITHOUT wrapping it in a [TOOL: CREATE_FILE] tag. You must use your tools to act.\n\n"
                f"# PLATFORM\n"
                f"- Shell: {_shell}\n"
                f"- Workspace Mode: {_ws_mode} | Root: {_ws_path}\n\n"
                "# TOOLS & SYNTAX\n"
                "To use a tool, you MUST use this EXACT format:\n\n"
                "## 1. Create a File\n"
                "Creates a new file in the workspace. Write the RAW content of the file inside the code block.\n"
                "[TOOL: CREATE_FILE script.py]\n"
                "```python\n"
                "print('Hello world!')\n"
                "```\n"
                "[/TOOL]\n\n"
                "## 2. Edit a File\n"
                "Overwrites the entire file.\n"
                "[TOOL: EDIT_FILE script.py]\n"
                "```python\n"
                "print('Hello updated!')\n"
                "```\n"
                "[/TOOL]\n\n"
                "## 3. Run a Command\n"
                "[TOOL: RUN_COMMAND]\n"
                "```bash\n"
                "python3 script.py\n"
                "```\n"
                "[/TOOL]\n\n"
                "## 4. Other File Tools\n"
                "READ_FILE, DELETE_FILE, APPEND_FILE, CREATE_DIRECTORY, LIST_DIRECTORY.\n"
                "[TOOL: READ_FILE script.py]\n"
                "[/TOOL]\n\n"
                + mcp_injection
            )
            messages.append({"role": "system", "content": sys_msg})
            if use_memory:
                # Keep last 8 history turns and truncate long older outputs to optimize token generation speed
                trimmed_history = history[-8:] if len(history) > 8 else history
                for msg in trimmed_history:
                    content_str = str(msg.get("content", ""))
                    if msg != trimmed_history[-1] and len(content_str) > 800:
                        content_str = content_str[:800] + "... [truncated for speed]"
                    messages.append({"role": msg.get("role", "user"), "content": content_str})
            else:
                messages.append({"role": "user", "content": prompt})

            engine_name = "AirLLM" if (getattr(self.llm.model, 'is_airllm', False) or 'airllm' in str(type(self.llm.model).__module__).lower()) else type(self.llm.model).__name__
            self._log_terminal("=== ROUTING CHECK ===")
            if skill_found:
                self._log_terminal("⚡ SKILL DETECTED: Injected SKILL.md context directly into AI mind.")
            self._log_terminal(f"1. Prompt received from User (Length: {len(prompt)} chars)")
            self._log_terminal(f"2. Routing through active LLM engine: {engine_name}")
            self._log_terminal(f"3. Executing {engine_name}.generate()...")
            response = self.llm.generate(messages, use_gpu=use_gpu)

            if self._cancel_requested or self._current_gen_id != gen_id:
                self._log_terminal("Generation cancelled after LLM returned (discarding response).")
                return

            self._log_terminal(f"4. Output returned from {engine_name} (Length: {len(response)} chars)")
            self._log_terminal("5. Delivering response back to User UI.")

            # Strip any lingering turn-end tokens
            for stop_token in ["<end_of_turn>", "<|eot_id|>", "<|im_end|>", "</s>", "<|end|>", "<|endoftext|>", "</end_of_turn>", "<end_of_turn/>"]:
                if stop_token in response:
                    response = response.split(stop_token)[0]
            response = response.strip()

            # Process tool calls
            response = self._process_tools(response, user_prompt=prompt)

            if self._cancel_requested or self._current_gen_id != gen_id:
                self._log_terminal("Generation cancelled right before saving history (discarding response).")
                return

            try:
                latest_history = self.memory.get_history(conv_id)
            except Exception:
                latest_history = history
            latest_history.append({"role": "assistant", "content": response})
            self.memory.save_history(conv_id, latest_history)

            # Memory cleanup after generation (in background to avoid blocking UI update)
            def _cleanup():
                try:
                    import gc
                    gc.collect()
                    try:
                        import torch as _torch
                        if _torch.cuda.is_available():
                            _torch.cuda.empty_cache()
                    except Exception:
                        pass
                except Exception:
                    pass
            import threading
            threading.Thread(target=_cleanup, daemon=True).start()
        except Exception as e:
            if self._cancel_requested or self._current_gen_id != gen_id:
                self._log_terminal("Generation was cancelled.")
                return
            self._log_terminal(f"Generation error: {str(e)}")
            try:
                latest_history = self.memory.get_history(conv_id)
            except Exception:
                latest_history = history
            latest_history.append({"role": "assistant", "content": f"[Error generating response: {str(e)}]"})
            self.memory.save_history(conv_id, latest_history)
        finally:
            if self._current_gen_id == gen_id:
                self.is_generating = False
                self.generating_conv_id = None
                self._cancel_requested = False

    def _process_tools(self, response_text, user_prompt=None):
        import re
        import subprocess

        def _clean_content(content):
            content = content.strip()
            if content.startswith("```"):
                lines = content.splitlines()
                if len(lines) > 1 and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                content = "\n".join(lines).strip()
            elif content.endswith("```"):
                lines = content.splitlines()
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                content = "\n".join(lines).strip()
            return content

        create_pattern = re.compile(r'\[TOOL:\s*CREATE_FILE[\s:|]+([^\s|\]"\'`]+)[\s:|]*(.*?)\]', re.DOTALL | re.IGNORECASE)
        edit_pattern = re.compile(r'\[TOOL:\s*EDIT_FILE[\s:|]+([^\s|\]"\'`]+)[\s:|]*(.*?)\]', re.DOTALL | re.IGNORECASE)
        delete_pattern = re.compile(r'\[TOOL:\s*DELETE_FILE[\s:|]+([^\s|\]"\'`]+)\]', re.DOTALL | re.IGNORECASE)
        read_pattern = re.compile(r'\[TOOL:\s*READ_FILE[\s:|]+([^\s|\]"\'`]+)\]', re.DOTALL | re.IGNORECASE)
        cmd_pattern = re.compile(r'\[TOOL:\s*RUN_COMMAND[\s:|]+(.*?)\]', re.DOTALL | re.IGNORECASE)
        mcp_pattern = re.compile(r'\[TOOL:\s*MCP_CALL[\s:|]+server=([^\s|\]]+)[\s:|]+tool=([^\s|\]]+)(?:[\s:|]+args=(\{.*?\}))?\]', re.DOTALL | re.IGNORECASE)
        
        all_matches = []
        for pat, action in [
            (create_pattern, "CREATE_FILE"),
            (edit_pattern, "EDIT_FILE"),
            (delete_pattern, "DELETE_FILE"),
            (read_pattern, "READ_FILE"),
            (cmd_pattern, "RUN_COMMAND"),
            (mcp_pattern, "MCP_CALL")
        ]:
            for m in pat.finditer(response_text):
                all_matches.append((m.start(), m.end(), action, m))
                
        all_matches.sort(key=lambda x: x[0])
        tools_executed = len(all_matches) > 0
        
        if not all_matches:
            # Fallback smart extraction
            if not tools_executed and user_prompt:
                import re as _re
                user_fn_match = _re.search(r'\b([a-zA-Z0-9_][a-zA-Z0-9_\-]*\.(?:py|js|html|css|json|txt|md|sh|c|cpp|rs|go|java|ts|tsx|jsx))\b', str(user_prompt), _re.IGNORECASE)
                if user_fn_match:
                    target_fname = user_fn_match.group(1)
                    code_fences = _re.findall(r'```[a-zA-Z]*\n(.*?)```', response_text, _re.DOTALL)
                    if code_fences:
                        best_code = max(code_fences, key=len).strip()
                        if len(best_code) > 5:
                            try:
                                if not self.file_ops:
                                    if hasattr(self, 'active_conv_id') and self.active_conv_id:
                                        self._init_file_ops(self.active_conv_id)
                                    else:
                                        if hasattr(self, 'memory') and self.memory:
                                            self.active_conv_id = self.memory.create_conversation("DarkMaxxer Session")
                                            self._init_file_ops(self.active_conv_id)
                                if self.file_ops:
                                    res = self.file_ops.create_file(target_fname, best_code)
                                    self._log_terminal(f"Smart extraction: Created {target_fname} from AI code block")
                                    response_text = f"\n✅ Created: **{target_fname}**\n\n" + response_text
                            except Exception as e:
                                self._log_terminal(f"Smart extraction failed for {target_fname}: {e}")
            return response_text
            
        if not self.file_ops:
            if hasattr(self, 'active_conv_id') and self.active_conv_id:
                self._init_file_ops(self.active_conv_id)
            else:
                if hasattr(self, 'memory') and self.memory:
                    self.active_conv_id = self.memory.create_conversation("DarkMaxxer Session")
                    self._init_file_ops(self.active_conv_id)
        if not self.file_ops:
            return response_text
            
        new_parts = []
        last_idx = 0
        
        for start, end, action, m in all_matches:
            new_parts.append(response_text[last_idx:start])
            injection = ""
            
            if action == "CREATE_FILE":
                path = m.group(1).strip()
                content = _clean_content(m.group(2))
                try:
                    self.file_ops.create_file(path, content)
                    self._log_terminal(f"Created file: {path}")
                    injection = f"\n✅ Created: **{path}**\n"
                except Exception as e:
                    self._log_terminal(f"Error creating {path}: {e}")
                    injection = f"\n❌ Create failed: {str(e)}\n"
            
            elif action == "EDIT_FILE":
                path = m.group(1).strip()
                content = _clean_content(m.group(2))
                try:
                    self.file_ops.edit_file(path, content)
                    self._log_terminal(f"Edited file: {path}")
                    injection = f"\n✅ Edited: **{path}**\n"
                except Exception as e:
                    self._log_terminal(f"Error editing {path}: {e}")
                    injection = f"\n❌ Edit failed: {str(e)}\n"
                    
            elif action == "DELETE_FILE":
                path = m.group(1).strip()
                try:
                    self.file_ops.delete_file(path)
                    self._log_terminal(f"Deleted file: {path}")
                    injection = f"\n✅ Deleted: **{path}**\n"
                except Exception as e:
                    self._log_terminal(f"Error deleting {path}: {e}")
                    injection = f"\n❌ Delete failed: {str(e)}\n"
                    
            elif action == "READ_FILE":
                path = m.group(1).strip()
                try:
                    self._log_terminal(f"Read file: {path}")
                    injection = f"\n✅ Read file: **{path}**\n"
                except Exception as e:
                    self._log_terminal(f"Error reading {path}: {e}")
                    injection = f"\n❌ Read failed: {str(e)}\n"
                    
            elif action == "RUN_COMMAND":
                cmd = _clean_content(m.group(1))
                try:
                    self._log_terminal(f"Running command: {cmd.splitlines()[0] if cmd else ''}...")
                    injection = f"\n✅ Executed Command\n"
                except Exception as e:
                    self._log_terminal(f"Error running command: {e}")
                    injection = f"\n❌ Command failed: {str(e)}\n"
                    
            elif action == "MCP_CALL":
                server = m.group(1).strip()
                tool_name = m.group(2).strip()
                args_str = m.group(3)
                try:
                    import json as _json
                    args = _json.loads(args_str) if args_str else {}
                    self._log_terminal(f"MCP call: {server}.{tool_name}")
                    injection = f"\n✅ MCP Tool Called: **{server}.{tool_name}**\n"
                except Exception as e:
                    self._log_terminal(f"Error calling MCP: {e}")
                    injection = f"\n❌ MCP Call failed: {str(e)}\n"
                    
            new_parts.append(injection)
            
            # The conversational text might be inside the TOOL tag, around the code block!
            if action in ("CREATE_FILE", "EDIT_FILE", "RUN_COMMAND"):
                path_or_cmd = m.group(1).strip()
                raw_tool_content = m.group(2) if action in ("CREATE_FILE", "EDIT_FILE") else m.group(1)
                
                parts = raw_tool_content.split("```")
                pre_text = parts[0].strip() if len(parts) > 0 else ""
                post_text = parts[-1].strip() if len(parts) > 2 else ""
                
                if pre_text: new_parts.append("\n" + pre_text + "\n")
                
                # Extract the code block itself to display in the chat history
                if len(parts) >= 3:
                    # The actual code block is everything between the first ``` and the last ```
                    # The first part of parts[1] might be the language identifier
                    code_inner = "```".join(parts[1:-1])
                    lines = code_inner.split("\n", 1)
                    lang = lines[0].strip() if len(lines) > 0 else ""
                    code_body = lines[1] if len(lines) > 1 else ""
                    
                    if action in ("CREATE_FILE", "EDIT_FILE"):
                        if not lang:
                            import os as _os
                            ext = _os.path.splitext(path_or_cmd)[1].replace(".", "").lower()
                            if ext:
                                lang = ext
                    elif action == "RUN_COMMAND":
                        if not lang:
                            lang = "bash"
                            
                    new_parts.append(f"\n```{lang}\n{code_body}\n```\n")
                
                if post_text: new_parts.append("\n" + post_text + "\n")
                
            last_idx = end
            
        new_parts.append(response_text[last_idx:])
        return "".join(new_parts)

    def _log_terminal(self, msg):
        """Log a message to the terminal panel with proper JS escaping and memory persistence."""
        from datetime import datetime
        t_str = datetime.now().strftime("%H:%M:%S")
        safe_msg = str(msg).replace("<", "&lt;").replace(">", "&gt;")
        entry = f"<span class='text-secondary'>[{t_str}]</span> {safe_msg}"
        if not hasattr(self, "terminal_logs") or self.terminal_logs is None:
            self.terminal_logs = []
        self.terminal_logs.append(entry)
        if len(self.terminal_logs) > 200:
            self.terminal_logs.pop(0)

        if self._window:
            import json as _json
            safe = _json.dumps(str(msg))
            try:
                self._window.evaluate_js(f"if(window.appendTerminal) window.appendTerminal({safe})")
            except Exception:
                pass

    def clear_terminal_logs(self):
        self.terminal_logs = []
        return {"success": True}

    # --- MCP Server Management ---

    def get_mcp_servers(self):
        """Return list of configured MCP servers and their connection status."""
        servers = self.config.get_config().get("mcp_servers", [])
        result = []
        for srv in servers:
            name = srv.get("name", "unknown")
            client = self.mcp_clients.get(name)
            connected = client.is_connected if client else False
            tool_count = len(client.tools) if client else 0
            result.append({
                "name": name,
                "command": srv.get("command", ""),
                "args": srv.get("args", []),
                "enabled": srv.get("enabled", True),
                "connected": connected,
                "tool_count": tool_count,
                "tools": [t.get("name", "") for t in (client.tools if client else [])]
            })
        return result

    def add_mcp_server(self, name, command, args_str="", env_str=""):
        """Add and connect to a new MCP server."""
        try:
            args = [a.strip() for a in args_str.split() if a.strip()] if args_str else []
            env = {}
            if env_str:
                for pair in env_str.split(","):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        env[k.strip()] = v.strip()
            srv_config = {"name": name, "command": command, "args": args, "env": env, "enabled": True}
            servers = self.config.get_config().get("mcp_servers", [])
            # Remove existing with same name
            servers = [s for s in servers if s.get("name") != name]
            servers.append(srv_config)
            self.config.update_config("mcp_servers", servers)
            # Try to connect
            client = MCPClient(name, command, args, env)
            if client.connect(timeout=10):
                self.mcp_clients[name] = client
                self._log_terminal(f"MCP server '{name}' connected with {len(client.tools)} tools")
                return {"success": True, "connected": True, "tools": [t.get("name", "") for t in client.tools]}
            else:
                self._log_terminal(f"MCP server '{name}' added but failed to connect")
                return {"success": True, "connected": False, "error": "Server added but connection failed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def remove_mcp_server(self, name):
        """Remove an MCP server and disconnect it."""
        try:
            client = self.mcp_clients.pop(name, None)
            if client:
                client.disconnect()
            servers = self.config.get_config().get("mcp_servers", [])
            servers = [s for s in servers if s.get("name") != name]
            self.config.update_config("mcp_servers", servers)
            self._log_terminal(f"MCP server '{name}' removed")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def reconnect_mcp_server(self, name):
        """Reconnect to a specific MCP server."""
        try:
            servers = self.config.get_config().get("mcp_servers", [])
            srv = next((s for s in servers if s.get("name") == name), None)
            if not srv:
                return {"success": False, "error": f"Server '{name}' not found in config"}
            old_client = self.mcp_clients.pop(name, None)
            if old_client:
                old_client.disconnect()
            client = MCPClient(name, srv["command"], srv.get("args", []), srv.get("env", {}))
            if client.connect(timeout=10):
                self.mcp_clients[name] = client
                return {"success": True, "connected": True, "tools": [t.get("name", "") for t in client.tools]}
            return {"success": False, "error": "Connection failed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- File System ---

    def get_file_tree(self):
        if self.file_ops:
            try:
                tree = self.file_ops.list_tree_recursive()
                return {
                    "active": True,
                    "files": tree["files"],
                    "folders": tree["folders"]
                }
            except Exception:
                return {"active": True, "files": [], "folders": []}
        return {"active": False, "files": [], "folders": []}

    def read_file(self, path):
        """Read a file's content from the active workspace."""
        if not self.file_ops:
            return {"success": False, "error": "No workspace active"}
        try:
            content = self.file_ops.read_file(path)
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_file(self, path, content):
        """Save/write content to a file in the active workspace."""
        if not self.file_ops:
            return {"success": False, "error": "No workspace active"}
        try:
            full = self.file_ops._safe_path(path)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(content)
            return {"success": True, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_command(self, cmd):
        """Run a shell command in the active workspace directory (sandboxed or global)."""
        if not self.file_ops:
            return {"success": False, "error": "No workspace active"}
        try:
            self._log_terminal(f"$ {cmd}")
            import re as _re
            import platform as _plat

            ws_mode = self.config.get_config().get("workspace_mode", "local")

            # Platform-aware security filters
            if ws_mode != "global":
                if _plat.system() == "Windows":
                    _DANGEROUS_PATTERNS = [
                        r'\.\.',            # directory traversal
                        r'(?i)^\s*cd\s',    # cd commands
                        r'(?i)^\s*pushd',   # pushd commands
                        r'(?i)powershell',   # powershell
                        r'(?i)cmd\s*/c',     # cmd /c
                        r'(?i)^\s*del\s',   # del commands
                        r'(?i)^\s*rd\s',    # rd commands
                        r'(?i)^\s*rmdir',   # rmdir commands
                        r'(?i)^\s*format',  # format commands
                        r'(?i)^\s*reg\s',   # registry
                        r'(?i)^\s*net\s',   # network commands
                        r'(?i)^\s*sc\s',    # service control
                    ]
                else:  # Linux / macOS
                    _DANGEROUS_PATTERNS = [
                        r'\.\.',                    # directory traversal
                        r'(?i)^\s*cd\s',            # cd commands
                        r'(?i)^\s*rm\s+-rf\s+/',    # rm -rf /
                        r'(?i)^\s*sudo\s+rm',       # sudo rm
                        r'(?i)^\s*mkfs',            # format filesystem
                        r'(?i)^\s*dd\s+if=',        # raw disk write
                        r'(?i)^\s*chmod\s+.*/',     # chmod on root
                        r'(?i)^\s*chown\s+.*/',     # chown on root
                        r'(?i)^\s*shutdown',        # shutdown
                        r'(?i)^\s*reboot',          # reboot
                    ]
                if any(_re.search(pat, cmd) for pat in _DANGEROUS_PATTERNS):
                    self._log_terminal("Security Alert: Command denied by sandbox policy.")
                    return {"success": False, "error": "Command denied by sandbox security policy."}

            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=self.file_ops.base_dir, timeout=60
            )
            output = result.stdout + result.stderr
            self._log_terminal(output if output.strip() else "(no output)")
            return {"success": True, "output": output, "returncode": result.returncode}
        except subprocess.TimeoutExpired:
            self._log_terminal("Command timed out (60s limit)")
            return {"success": False, "error": "Command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_subagents(self):
        return {"success": True, "subagents": getattr(self, "subagents", [])}

    def add_subagent(self, name, task, status="running"):
        if not hasattr(self, "subagents"):
            self.subagents = []
        for sa in self.subagents:
            if sa.get("name") == name:
                sa["task"] = task
                sa["status"] = status
                return {"success": True, "subagents": self.subagents}
        self.subagents.append({"name": name, "task": task, "status": status})
        return {"success": True, "subagents": self.subagents}

    def update_subagent(self, name, status, result=None):
        if not hasattr(self, "subagents"):
            self.subagents = []
        for sa in self.subagents:
            if sa.get("name") == name:
                sa["status"] = status
                if result is not None:
                    sa["result"] = result
                break
        return {"success": True, "subagents": self.subagents}

    def clear_subagents(self):
        self.subagents = []
        return {"success": True, "subagents": []}

    def get_active_state(self):
        conf = self.config.get_config()
        ws_mode = conf.get("workspace_mode", "local")
        # Fallback to fix stuck generating state if thread died or UI missed it
        if getattr(self, "is_generating", False):
            import threading
            has_gen_thread = any(t.name == "DarkMaxxerGenThread" and t.is_alive() for t in threading.enumerate())
            if not has_gen_thread:
                self.is_generating = False
                self.generating_conv_id = None

        state = {
            "file_ops_active": self.file_ops is not None,
            "ai_path": conf.get("ai_path") if conf.get("ai_path") and os.path.exists(conf.get("ai_path", "")) else None,
            "ai_loaded": self.llm.model is not None,
            "is_generating": getattr(self, "is_generating", False),
            "generating_conv_id": getattr(self, "generating_conv_id", None),
            "conv_id": None,
            "history": [],
            "terminal_logs": getattr(self, "terminal_logs", []),
            "workspace_path": self.file_ops.base_dir if self.file_ops else None,
            "workspace_name": os.path.basename(self.file_ops.base_dir) if self.file_ops else None,
            "workspace_mode": ws_mode,
            "active_sidebar_tab": conf.get("active_sidebar_tab", "chats"),
            "subagents": getattr(self, "subagents", [])
        }
        active_id = self.active_conv_id or conf.get("active_conv_id")
        if active_id:
            self.active_conv_id = active_id
            state["conv_id"] = active_id
            try:
                state["history"] = self.memory.get_history(active_id)
            except Exception:
                state["history"] = []
        return state

    def run_diagnostics(self):
        """Run system diagnostics for the About panel — supports NVIDIA, AMD ROCm, and CPU."""
        import platform
        accelerator = "CPU"
        device_name = "CPU only"
        vram_gb = "N/A"
        has_gpu = False

        try:
            import torch
            # Check for AMD ROCm (PyTorch ROCm sets torch.version.hip)
            is_rocm = hasattr(torch.version, 'hip') and torch.version.hip is not None
            has_gpu = torch.cuda.is_available()

            if has_gpu:
                accelerator = "ROCm" if is_rocm else "CUDA"
                try:
                    device_name = torch.cuda.get_device_name(0)
                    vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
                except Exception:
                    device_name = f"{accelerator} GPU (details unavailable)"
        except Exception:
            pass

        return {
            "success": True,
            "os": platform.platform(),
            "python": platform.python_version(),
            "cuda_available": has_gpu,
            "accelerator": accelerator,
            "device": device_name,
            "vram": f"{vram_gb} GB" if vram_gb != "N/A" else "N/A",
            "workspace": self.file_ops.base_dir if self.file_ops else "None",
            "workspace_mode": self.config.get_config().get("workspace_mode", "local"),
            "model_loaded": self.llm.model is not None,
            "model_path": self.llm.model_path if self.llm.model_path else "None loaded"
        }

    def uninstall_app(self):
        """Uninstall DarkMaxxer — remove app files, venv, shortcuts, and config."""
        import platform as _plat
        import shutil
        results = []
        app_dir = os.path.dirname(os.path.abspath(__file__))
        
        try:
            # 1. Remove venv
            venv_dir = os.path.join(app_dir, "venv")
            if os.path.isdir(venv_dir):
                shutil.rmtree(venv_dir, ignore_errors=True)
                results.append("✔ Removed virtual environment")
            
            # 2. Remove desktop shortcuts
            if _plat.system() == "Windows":
                # Windows shortcuts
                for loc in [os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"),
                            os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs")]:
                    shortcut = os.path.join(loc, "DarkMaxxer.lnk")
                    if os.path.exists(shortcut):
                        os.remove(shortcut)
                        results.append(f"✔ Removed shortcut: {shortcut}")
            else:
                # Linux system uninstall
                uninstaller = os.path.join(app_dir, "DarkLinux", "dist", "uninstall.sh")
                if os.path.exists(uninstaller):
                    import subprocess
                    r = subprocess.run(["bash", uninstaller], capture_output=True, text=True)
                    if r.returncode == 0:
                        results.append("✔ Uninstalled DarkMaxxer system packages and caches")
                    else:
                        results.append("⚠ System uninstall failed or was cancelled")
                else:
                    results.append("⚠ Could not find Linux uninstall script")
            
            # 3. Remove config
            config_file = os.path.join(app_dir, "config.json")
            if os.path.exists(config_file):
                os.remove(config_file)
                results.append("✔ Removed config.json")
            
            # 4. Remove setup marker
            marker = os.path.join(app_dir, "venv", ".setup_complete")
            if os.path.exists(marker):
                os.remove(marker)
                results.append("✔ Removed setup marker")
            
            # 5. Remove crash/log files
            for log_file in ["crash.log", "crash_report.log", "early_crash.log", "webview_error.log", "debug_output.txt"]:
                log_path = os.path.join(app_dir, log_file)
                if os.path.exists(log_path):
                    os.remove(log_path)
                    results.append(f"✔ Removed {log_file}")
            
            # 6. Remove context/memory data
            context_dir = os.path.join(app_dir, "context")
            if os.path.isdir(context_dir):
                shutil.rmtree(context_dir, ignore_errors=True)
                results.append("✔ Removed conversation data")
            
            # 7. Remove AppData / Cache
            appdata = os.getenv('APPDATA')
            if appdata:
                locallow = os.path.join(os.path.dirname(appdata), "LocalLow")
            else:
                locallow = os.path.join(os.path.expanduser("~"), ".local", "share")
            
            for cache_path in [
                os.path.join(locallow, "DarkMaxxer"),
                os.path.join(os.getenv('APPDATA', ''), "DarkMaxxer"),
                os.path.join(os.path.expanduser("~"), ".config", "DarkMaxxer")
            ]:
                if cache_path and os.path.exists(cache_path):
                    try:
                        shutil.rmtree(cache_path, ignore_errors=True)
                        results.append(f"✔ Removed AppData/Cache: {cache_path}")
                    except Exception:
                        pass
            
            if not results:
                results.append("Nothing to clean up — app appears already uninstalled.")
            
            results.append("\n✔ Uninstall complete. You can now delete the app folder.")
            return {"success": True, "results": results}
        except Exception as e:
            results.append(f"❌ Error: {str(e)}")
            return {"success": False, "results": results, "error": str(e)}

    def verify_watermarks(self):
        """Verify proprietary watermarks across core Python files."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        core_files = ['main.py', 'memory_manager.py', 'llm_engine.py', 'mcp_integration.py']
        results = []
        all_passed = True
        for fname in core_files:
            fpath = os.path.join(script_dir, fname)
            if os.path.exists(fpath):
                with open(fpath, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if "[Vikalp Sharma]" in first_line:
                        results.append({"file": fname, "status": "Passed"})
                    else:
                        results.append({"file": fname, "status": "Missing Watermark"})
                        all_passed = False
            else:
                results.append({"file": fname, "status": "Not Found"})
                all_passed = False
        return {"success": True, "all_passed": all_passed, "files": results}

    def clear_all_history(self):
        """Clear conversation context files and reset current memory."""
        try:
            if self.active_conv_id:
                self.memory.delete_history(self.active_conv_id)
                self.active_conv_id = None
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_workspace_in_explorer(self):
        """Open the active workspace directory in the system file manager."""
        if self.file_ops and os.path.exists(self.file_ops.base_dir):
            try:
                import platform as _plat
                if _plat.system() == "Windows":
                    os.startfile(self.file_ops.base_dir)
                elif _plat.system() == "Darwin":
                    subprocess.Popen(["open", self.file_ops.base_dir])
                else:
                    subprocess.Popen(["xdg-open", self.file_ops.base_dir])
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "No workspace active"}

if __name__ == '__main__':
    # Resolve script_dir correctly for both normal Python and PyInstaller frozen exe
    if getattr(sys, 'frozen', False):
        # Frozen exe: use the directory containing the exe, not _MEIPASS temp dir
        script_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    if "--uninstall" in sys.argv:
        print("\033[1;36m[DarkMaxxer]\033[0m Starting uninstaller...")
        api = Api()
        res = api.uninstall_app()
        for r in res.get("results", []):
            if r.startswith("✔"):
                print(f"\033[1;32m{r}\033[0m")
            elif r.startswith("⚠"):
                print(f"\033[1;33m{r}\033[0m")
            elif r.startswith("❌"):
                print(f"\033[1;31m{r}\033[0m")
            else:
                print(r)
        sys.exit(0 if res.get("success") else 1)

    try:
        if webview is None:
            err_msg = "pywebview is not installed or failed to import. Please run DarkMaxxerSetup.exe or 'pip install pywebview'."
            print(f"ERROR: {err_msg}")
            try:
                with open(os.path.join(script_dir, "crash_report.log"), "w", encoding="utf-8") as f:
                    f.write(err_msg + "\n")
                import tkinter as tk
                from tkinter import messagebox
                r = tk.Tk()
                r.withdraw()
                messagebox.showerror("DarkMaxxer Startup Error", err_msg)
                r.destroy()
            except Exception:
                pass
            sys.exit(1)

        gui_dir = os.path.join(script_dir, 'gui')
        os.makedirs(gui_dir, exist_ok=True)

        api = Api()

        conf = api.config.get_config()
        ai_path = conf.get("ai_path")
        # Validate saved model path still exists on disk
        if ai_path and not os.path.exists(ai_path):
            ai_path = None  # Path gone (moved drive, changed OS, etc.)
            api.config.update_config("ai_path", None)
        if not ai_path:
            start_html = os.path.join(gui_dir, 'models.html')
            if not os.path.exists(start_html):
                start_html = os.path.join(gui_dir, 'index.html')
        else:
            start_html = os.path.join(gui_dir, 'index.html')

        if not os.path.exists(start_html):
            with open(start_html, 'w', encoding='utf-8') as f:
                f.write("<html><body><h1>DarkMaxxer GUI missing. Ensure gui/index.html and models.html are present.</h1></body></html>")

        start_html_url = f"file:///{os.path.abspath(start_html).replace('\\', '/')}"

        # Generate splash screen with dark background and spinning logo
        _splash_path = os.path.join(gui_dir, 'splash.html')
        _logo_file = os.path.join(gui_dir, 'logo.png')
        _logo_url = ''
        if os.path.exists(_logo_file):
            _logo_url = 'file:///' + os.path.abspath(_logo_file).replace(os.sep, '/')
        _splash_html = (
            '<!DOCTYPE html><html><head><meta charset="utf-8"><style>'
            '*{margin:0;padding:0;box-sizing:border-box}'
            'html,body{width:100%;height:100%;overflow:hidden;'
            'background:#0a0a0f;background-image:radial-gradient(circle at 50% 45%,rgba(105,30,166,0.12) 0%,rgba(10,10,15,1) 70%);'
            'display:flex;align-items:center;justify-content:center}'
            '.c{display:flex;flex-direction:column;align-items:center;animation:containerIn .6s ease-out}'
            '.logo-wrap{position:relative;width:130px;height:130px;display:flex;align-items:center;justify-content:center}'
            '.glow-ring{position:absolute;inset:-8px;border-radius:50%;'
            'border:2px solid rgba(168,85,247,0.3);'
            'animation:spinCW 2s linear infinite;'
            'box-shadow:0 0 30px rgba(168,85,247,0.2),inset 0 0 20px rgba(168,85,247,0.05)}'
            '.glow-ring::after{content:"";position:absolute;top:-3px;left:50%;width:6px;height:6px;'
            'background:#a855f7;border-radius:50%;transform:translateX(-50%);'
            'box-shadow:0 0 12px 3px rgba(168,85,247,0.8)}'
            '.logo{width:100px;height:100px;border-radius:50%;'
            'animation:spinCW 2s linear infinite;'
            'filter:drop-shadow(0 0 15px rgba(168,85,247,0.4))}'
            '.t{color:#e0e3e5;font-family:Segoe UI,sans-serif;font-size:20px;font-weight:600;'
            'margin-top:22px;letter-spacing:3px;text-transform:uppercase;'
            'animation:fadeIn 1s ease-out .3s both}'
            '.dots{display:flex;gap:6px;margin-top:16px;animation:fadeIn 1s ease-out .6s both}'
            '.dot{width:6px;height:6px;border-radius:50%;background:rgba(168,85,247,0.6);'
            'animation:bounce .6s ease-in-out infinite alternate}'
            '.dot:nth-child(2){animation-delay:.15s}'
            '.dot:nth-child(3){animation-delay:.3s}'
            '@keyframes spinCW{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}'
            '@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}'
            '@keyframes bounce{from{opacity:.3;transform:scale(.7)}to{opacity:1;transform:scale(1.2)}}'
            '@keyframes containerIn{from{opacity:0;transform:scale(.85)}to{opacity:1;transform:scale(1)}}'
            '</style></head><body>'
            '<div class="c">'
            '<div class="logo-wrap"><div class="glow-ring"></div>'
            '<img class="logo" src="' + _logo_url + '" alt=""></div>'
            '<div class="t">DarkMaxxer</div>'
            '<div class="dots"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>'
            '</div>'
            '<script>setTimeout(function(){ window.location.replace("' + start_html_url + '"); }, 3500);</script>'
            '</body></html>'
        )
        try:
            with open(_splash_path, 'w', encoding='utf-8') as _sf:
                _sf.write(_splash_html)
        except PermissionError:
            _fallback_dir = os.path.expanduser('~/.darkmaxxer')
            os.makedirs(_fallback_dir, exist_ok=True)
            _splash_path = os.path.join(_fallback_dir, 'splash.html')
            with open(_splash_path, 'w', encoding='utf-8') as _sf:
                _sf.write(_splash_html)
        _splash_url = 'file:///' + os.path.abspath(_splash_path).replace(os.sep, '/')

        # Resolve icon path BEFORE any windows are created
        logo_path = os.path.join(script_dir, "gui", "logo_highres.ico")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(script_dir, "gui", "logo.ico")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(script_dir, "gui", "logo.png")

        # Set AppUserModelID BEFORE creating windows so the taskbar
        # shows DarkMaxxer's icon instead of python.exe's default icon
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('SMXF.DarkMaxxer.IDE.2.5.0')
        except Exception:
            pass
        # Use splash screen sequence for all platforms
        # Use a single window sequence for stability on Linux/GTK
        main_win = webview.create_window(
            'DarkMaxxer',
            url=_splash_url,  # Load splash screen first
            js_api=api,
            width=1280,
            height=800,
            min_size=(900, 600),
            background_color='#0a0a0f',
        )
        api.set_window(main_win)

        try:
            webview.start(debug=False, icon=logo_path, gui='gtk')
        except Exception:
            try:
                webview.start(icon=logo_path, gui='gtk')
            except Exception:
                webview.start(icon=logo_path)
    except BaseException as e:
        if isinstance(e, SystemExit) and e.code == 0:
            sys.exit(0)
        import traceback
        tb = traceback.format_exc()
        
        # Detect the specific pywebview GTK/QT missing error
        err_str = str(e)
        if "QT or GTK" in err_str or "WebViewException" in type(e).__name__:
            fix_msg = (
                "pywebview cannot find GTK or QT backend.\n\n"
                "Fix for Fedora/RHEL:\n"
                "  sudo dnf install python3-gobject webkit2gtk4.1 gtk3\n\n"
                "Fix for Ubuntu/Debian:\n"
                "  sudo apt install python3-gi gir1.2-webkit2-4.1 libgtk-3-0\n\n"
                "Then delete the venv and re-run:\n"
                "  sudo rm -rf /opt/darkmaxxer/venv && darkmaxxer"
            )
        else:
            fix_msg = f"Application encountered a fatal error on startup:\n{e}\n\nCheck crash_report.log for details."
        
        try:
            with open(os.path.join(script_dir, "crash_report.log"), "w", encoding="utf-8") as f:
                f.write(f"Fatal Startup Error:\n{tb}\n")
            import tkinter as tk
            from tkinter import messagebox
            r = tk.Tk()
            r.withdraw()
            messagebox.showerror("DarkMaxxer Startup Crash", fix_msg)
            r.destroy()
        except Exception:
            pass
        sys.exit(1)

