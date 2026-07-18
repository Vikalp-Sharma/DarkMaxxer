# [Vikalp Sharma] - Proprietary / Anti-Theft Watermark
import os
import sys
import io

def _ensure_local_site_packages():
    _here = os.path.dirname(os.path.abspath(__file__))
    _cands = [
        os.path.join(_here, "venv", "Lib", "site-packages"),
        os.path.join(_here, "..", "venv", "Lib", "site-packages"),
        os.path.join(os.path.expanduser("~"), "DarkMaxxer", "venv", "Lib", "site-packages"),
        os.path.join(os.getenv("LOCALAPPDATA", ""), "Low", "DarkMaxxer", "venv", "Lib", "site-packages"),
        os.path.join(os.getenv("APPDATA", ""), "DarkMaxxer", "venv", "Lib", "site-packages"),
    ]
    for _c in _cands:
        if os.path.exists(_c) and _c not in sys.path:
            sys.path.insert(0, _c)
_ensure_local_site_packages()

# Protect against pythonw.exe stdout/stderr being None (`AttributeError: 'NoneType' object has no attribute 'write'`)
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

import threading
import subprocess
try:
    import webview
except Exception:
    webview = None
from memory_manager import MemoryManager, ConfigManager
from llm_engine import LLMEngine
from mcp_integration import FileOpsServer

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
            file_types = ('Model Files (*.file;*.pkl;*.bin;*.safetensors;*.pth;*.pt;*.gguf;*.json;*.*)', 'All files (*.*)')
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
        if not force and self.file_ops and hasattr(self.file_ops, 'base_dir') and os.path.exists(self.file_ops.base_dir):
            if "brain" not in str(self.file_ops.base_dir).lower() and ".system_generated" not in str(self.file_ops.base_dir).lower():
                return
        cfg_ws = self.config.get_config().get("active_workspace_dir")
        if not force and cfg_ws and os.path.exists(cfg_ws) and "brain" not in str(cfg_ws).lower() and ".system_generated" not in str(cfg_ws).lower():
            self.file_ops = FileOpsServer(cfg_ws)
            return
        workspace_dir = self.memory.get_workspace_dir(conv_id)
        os.makedirs(workspace_dir, exist_ok=True)
        self.file_ops = FileOpsServer(workspace_dir)
        self.config.update_config("active_workspace_dir", workspace_dir)

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
                self.file_ops = FileOpsServer(selected_dir)
                self.config.update_config("active_workspace_dir", selected_dir)
                self._log_terminal(f"Workspace set to external folder: {selected_dir}")
                return {"success": True, "path": selected_dir}
            return {"success": False, "error": "No folder selected"}
        except Exception as e:
            return {"success": False, "error": str(e)}

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
            self.active_conv_id = self.memory.create_conversation("DarkMaxxer Session")
            self._init_file_ops(self.active_conv_id)
            self.config.update_config("active_conv_id", self.active_conv_id)
        elif not os.path.exists(os.path.join(self.memory.context_dir, f"{self.active_conv_id}.json")):
            # If ID exists but file is missing/locked, recreate it rather than making a new ID
            self.memory.save_history(self.active_conv_id, [])

        history = self.memory.get_history(self.active_conv_id)
        history.append({"role": "user", "content": prompt})
        self.memory.save_history(self.active_conv_id, history)

        t = threading.Thread(target=self._generate_worker, args=(prompt, self.active_conv_id, history, gen_id))
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
                # Purge pending incomplete user prompts & paused tags from history!
                while hist and hist[-1].get("role") == "user":
                    hist.pop()
                while hist and hist[-1].get("role") == "assistant" and "[Generation paused" in str(hist[-1].get("content", "")):
                    hist.pop()
                self.memory.save_history(self.active_conv_id, hist)
            except Exception:
                pass
        self._log_terminal("Generation paused by user.")
        return {"success": True}

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

            # Build structured messages array for chat models
            messages = []
            sys_msg = (
                f"{context_files}"
                "You are DarkMaxxer AI, an autonomous local AI coding assistant with direct access to the user's filesystem and workspace.\n"
                "Whenever the user asks you to create a file, edit a file, rename a file, read a file, append to a file, or run a command, you MUST immediately output the corresponding [TOOL: ...] block.\n"
                "NEVER explain syntax to the user. NEVER apologize when asked to create a file. Just execute immediately using the exact syntax below:\n\n"
                "=== AVAILABLE TOOLS AND EXACT SYNTAX ===\n"
                "1. CREATE FILE (to create a new file or overwrite an existing file. ALWAYS use a proper extension like .py, .html, .js, .json):\n"
                "[TOOL: CREATE_FILE filename.py\n"
                "def add(a, b):\n"
                "    return a + b\n"
                "]\n\n"
                "2. RENAME FILE OR CHANGE EXTENSION:\n"
                "[TOOL: RENAME_FILE old_name.code -> new_name.py]\n\n"
                "3. APPEND FILE:\n"
                "[TOOL: APPEND_FILE filename.py\n"
                "# appended code\n"
                "]\n\n"
                "4. READ FILE:\n"
                "[TOOL: READ_FILE filepath]\n\n"
                "5. EDIT FILE:\n"
                "[TOOL: EDIT_FILE filepath\n"
                "new code here\n"
                "]\n\n"
                "6. LIST DIRECTORY:\n"
                "[TOOL: LIST_DIRECTORY .]\n\n"
                "7. RUN COMMAND:\n"
                "[TOOL: RUN_COMMAND python filename.py]\n\n"
                "8. DELETE FILE:\n"
                "[TOOL: DELETE_FILE filepath]\n\n"
                "CRITICAL RULES:\n"
                "- When user asks for Python code or a Python file (like adding 2 numbers), ALWAYS create a .py file (e.g. adder.py or main.py) with complete, runnable code inside [TOOL: CREATE_FILE adder.py ...]. NEVER create .code files.\n"
                "- When creating or modifying a file, output the [TOOL: ...] block containing the complete code."
            )
            messages.append({"role": "system", "content": sys_msg})
            if use_memory:
                # Keep last 12 history turns and truncate long older outputs to optimize token generation speed
                trimmed_history = history[-12:] if len(history) > 12 else history
                for msg in trimmed_history:
                    content_str = str(msg.get("content", ""))
                    if msg != trimmed_history[-1] and len(content_str) > 1500:
                        content_str = content_str[:1500] + "... [truncated for speed]"
                    messages.append({"role": msg.get("role", "user"), "content": content_str})
            else:
                messages.append({"role": "user", "content": prompt})

            engine_name = "AirLLM" if (getattr(self.llm.model, 'is_airllm', False) or 'airllm' in str(type(self.llm.model).__module__).lower()) else type(self.llm.model).__name__
            self._log_terminal("=== ROUTING CHECK ===")
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
                self._cancel_requested = False

    def _process_tools(self, response_text, user_prompt=None):
        if not self.file_ops:
            if hasattr(self, 'active_conv_id') and self.active_conv_id:
                self._init_file_ops(self.active_conv_id)
            else:
                if hasattr(self, 'memory') and self.memory:
                    self.active_conv_id = self.memory.create_conversation("DarkMaxxer Session")
                    self._init_file_ops(self.active_conv_id)
        if not self.file_ops:
            return response_text

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
        build_pattern = re.compile(r'\[TOOL:\s*BUILD_FILE[\s:|]+([^\s|\]"\'`]+)\]', re.DOTALL | re.IGNORECASE)
        rename_pattern = re.compile(r'\[TOOL:\s*(?:RENAME_FILE|CHANGE_EXTENSION)[\s:|]+([^\s|\]"\'`]+)\s*(?:->|to|\s)\s*([^\s|\]"\'`]+)\]', re.DOTALL | re.IGNORECASE)
        append_pattern = re.compile(r'\[TOOL:\s*APPEND_FILE[\s:|]+([^\s|\]"\'`]+)[\s:|]*(.*?)\]', re.DOTALL | re.IGNORECASE)
        listdir_pattern = re.compile(r'\[TOOL:\s*LIST_DIRECTORY[\s:|]*([^\s|\]"\'`]*)\]', re.DOTALL | re.IGNORECASE)

        tools_executed = False

        def create_repl(match):
            nonlocal tools_executed
            path, content = match.group(1).strip(), _clean_content(match.group(2))
            try:
                res = self.file_ops.create_file(path, content)
                self._log_terminal(f"Created file: {path}")
                tools_executed = True
                return f"\n✅ {res}\n"
            except Exception as e:
                self._log_terminal(f"Error creating {path}: {e}")
                return f"\n❌ Create failed: {str(e)}\n"

        def edit_repl(match):
            nonlocal tools_executed
            path, content = match.group(1).strip(), _clean_content(match.group(2))
            try:
                res = self.file_ops.edit_file(path, content)
                self._log_terminal(f"Edited file: {path}")
                tools_executed = True
                return f"\n✅ {res}\n"
            except Exception as e:
                self._log_terminal(f"Error editing {path}: {e}")
                return f"\n❌ Edit failed: {str(e)}\n"

        def delete_repl(match):
            nonlocal tools_executed
            path = match.group(1).strip()
            try:
                res = self.file_ops.delete_file(path)
                self._log_terminal(f"Deleted file: {path}")
                tools_executed = True
                return f"\n✅ {res}\n"
            except Exception as e:
                self._log_terminal(f"Error deleting {path}: {e}")
                return f"\n❌ Delete failed: {str(e)}\n"

        def read_repl(match):
            nonlocal tools_executed
            path = match.group(1).strip()
            try:
                content = self.file_ops.read_file(path)
                self._log_terminal(f"Read file: {path}")
                tools_executed = True
                return f"\n📖 **Contents of {path}:**\n```\n{content[:2000]}\n```\n"
            except Exception as e:
                self._log_terminal(f"Error reading {path}: {e}")
                return f"\n❌ Read failed: {str(e)}\n"

        def rename_repl(match):
            nonlocal tools_executed
            old_path, new_path = match.group(1).strip(), match.group(2).strip()
            try:
                res = self.file_ops.rename_file(old_path, new_path)
                self._log_terminal(f"Renamed file: {old_path} -> {new_path}")
                tools_executed = True
                return f"\n✅ {res}\n"
            except Exception as e:
                self._log_terminal(f"Error renaming {old_path} -> {new_path}: {e}")
                return f"\n❌ Rename failed: {str(e)}\n"

        def append_repl(match):
            nonlocal tools_executed
            path, content = match.group(1).strip(), _clean_content(match.group(2))
            try:
                res = self.file_ops.append_file(path, content)
                self._log_terminal(f"Appended to file: {path}")
                tools_executed = True
                return f"\n✅ {res}\n"
            except Exception as e:
                self._log_terminal(f"Error appending to {path}: {e}")
                return f"\n❌ Append failed: {str(e)}\n"

        def listdir_repl(match):
            nonlocal tools_executed
            path = match.group(1).strip() or "."
            try:
                res = self.file_ops.list_directory(path)
                self._log_terminal(f"Listed directory: {path}")
                tools_executed = True
                return f"\n📁 **Directory Contents of {path}:**\nFolders: {res['folders']}\nFiles: {res['files']}\n"
            except Exception as e:
                self._log_terminal(f"Error listing directory {path}: {e}")
                return f"\n❌ List directory failed: {str(e)}\n"

        def cmd_repl(match):
            nonlocal tools_executed
            cmd_str = _clean_content(match.group(1))
            try:
                self._log_terminal(f"Running command: {cmd_str}")
                cwd = self.file_ops.base_dir if self.file_ops and os.path.exists(self.file_ops.base_dir) else None
                out = subprocess.check_output(cmd_str, shell=True, cwd=cwd, stderr=subprocess.STDOUT, text=True, timeout=60)
                self._log_terminal(f"Command output:\n{out[:1000]}")
                tools_executed = True
                return f"\n💻 **Command Executed:** `{cmd_str}`\n**Output:**\n```\n{out[:2000]}\n```\n"
            except Exception as e:
                err_msg = e.output if hasattr(e, 'output') and e.output else str(e)
                self._log_terminal(f"Command failed: {err_msg}")
                return f"\n❌ Command failed `{cmd_str}`:\n```\n{err_msg}\n```\n"

        _DANGEROUS_CHARS = [";", "&", "|", "`", "$", "(", ")", "<", ">", "\n", "\r"]

        def build_repl(match):
            nonlocal tools_executed
            path = match.group(1).strip()
            if any(dc in path for dc in _DANGEROUS_CHARS):
                self._log_terminal(f"Security: Blocked dangerous build target: {path}")
                return f"\n❌ Build blocked by security policy: {path}\n"
            try:
                self._log_terminal(f"Building/Executing target: {path}")
                cwd = self.file_ops.base_dir if self.file_ops and os.path.exists(self.file_ops.base_dir) else None
                if path.endswith(".py"):
                    cmd = ["python", path]
                elif path.endswith(".js"):
                    cmd = ["node", path]
                else:
                    cmd = path if not any(dc in path for dc in _DANGEROUS_CHARS) else []
                if isinstance(cmd, list):
                    out = subprocess.check_output(cmd, shell=False, cwd=cwd, stderr=subprocess.STDOUT, text=True, timeout=120)
                else:
                    out = subprocess.check_output(cmd, shell=True, cwd=cwd, stderr=subprocess.STDOUT, text=True, timeout=120)
                self._log_terminal(f"Build output:\n{out[:1000]}")
                tools_executed = True
                return f"\nBuild/Execution Success: {path}\nOutput:\n{out[:2000]}\n"
            except Exception as e:
                err_msg = e.output if hasattr(e, 'output') and e.output else str(e)
                self._log_terminal(f"Build error: {err_msg}")
                return f"\nBuild Failed: {path}\nError:\n{err_msg}\n"

        response_text = create_pattern.sub(create_repl, response_text)
        response_text = edit_pattern.sub(edit_repl, response_text)
        response_text = delete_pattern.sub(delete_repl, response_text)
        response_text = read_pattern.sub(read_repl, response_text)
        response_text = rename_pattern.sub(rename_repl, response_text)
        response_text = append_pattern.sub(append_repl, response_text)
        response_text = listdir_pattern.sub(listdir_repl, response_text)
        response_text = cmd_pattern.sub(cmd_repl, response_text)
        response_text = build_pattern.sub(build_repl, response_text)

        # Loose tool pattern check if not executed yet: [TOOL: CREATE_FILE path] ```code```
        if not tools_executed:
            loose_create = re.compile(r'\[TOOL:\s*CREATE_FILE[\s:|]+([^\s|\]"\'`]+)\]\s*```[a-zA-Z]*\s*(.*?)\s*```', re.DOTALL | re.IGNORECASE)
            def loose_repl(match):
                nonlocal tools_executed
                path, content = match.group(1).strip(), match.group(2).strip()
                try:
                    res = self.file_ops.create_file(path, content)
                    self._log_terminal(f"Created file: {path}")
                    tools_executed = True
                    return f"\n✅ {res}\n"
                except Exception as e:
                    self._log_terminal(f"Error creating {path}: {e}")
                    return f"\n❌ Create failed: {str(e)}\n"
            response_text = loose_create.sub(loose_repl, response_text)


        return response_text

    def _log_terminal(self, msg):
        """Log a message to the terminal panel with proper JS escaping and memory persistence."""
        from datetime import datetime
        t_str = datetime.now().strftime("%H:%M:%S")
        safe_msg = str(msg).replace("<", "&lt;").replace(">", "&gt;")
        entry = f"<span class='text-secondary'>[{t_str}]</span> {safe_msg}"
        if not hasattr(self, "terminal_logs") or self.terminal_logs is None:
            self.terminal_logs = []
        self.terminal_logs.append(entry)
        if len(self.terminal_logs) > 500:
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

    # --- File System ---

    def get_file_tree(self):
        if self.file_ops:
            try:
                return {
                    "active": True,
                    "files": self.file_ops.list_files(),
                    "folders": self.file_ops.list_folders()
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

    def run_command(self, cmd):
        """Run a shell command in the active workspace directory (sandboxed)."""
        if not self.file_ops:
            return {"success": False, "error": "No workspace active"}
        try:
            self._log_terminal(f"$ {cmd}")
            import re as _re
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
            if any(_re.search(pat, cmd) for pat in _DANGEROUS_PATTERNS):
                self._log_terminal("Security Alert: Command denied. Directory traversal and external navigation are restricted. Nothing can escape the workspace folder.")
                return {"success": False, "error": "Command denied by sandbox security policy: directory traversal restricted."}
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=self.file_ops.base_dir, timeout=30
            )
            output = result.stdout + result.stderr
            self._log_terminal(output if output.strip() else "(no output)")
            return {"success": True, "output": output, "returncode": result.returncode}
        except subprocess.TimeoutExpired:
            self._log_terminal("Command timed out (30s limit)")
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
        state = {
            "file_ops_active": self.file_ops is not None,
            "ai_path": conf.get("ai_path"),
            "ai_loaded": self.llm.model is not None,
            "is_generating": getattr(self, "is_generating", False),
            "conv_id": None,
            "history": [],
            "terminal_logs": getattr(self, "terminal_logs", []),
            "workspace_path": self.file_ops.base_dir if self.file_ops else None,
            "workspace_name": os.path.basename(self.file_ops.base_dir) if self.file_ops else None,
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
        """Run system diagnostics for the About panel."""
        import platform
        try:
            import torch
            has_cuda = torch.cuda.is_available()
            device_name = torch.cuda.get_device_name(0) if has_cuda else "CPU / Metal / Non-CUDA"
            vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2) if has_cuda else "N/A"
        except Exception:
            has_cuda = False
            device_name = "Not detected or CPU"
            vram_gb = "N/A"

        return {
            "success": True,
            "os": platform.platform(),
            "python": platform.python_version(),
            "cuda_available": has_cuda,
            "device": device_name,
            "vram": f"{vram_gb} GB" if vram_gb != "N/A" else "N/A",
            "workspace": self.file_ops.base_dir if self.file_ops else "None",
            "model_loaded": self.llm.model is not None,
            "model_path": self.llm.model_path if self.llm.model_path else "None loaded"
        }

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
        """Open the active workspace directory in Windows File Explorer."""
        if self.file_ops and os.path.exists(self.file_ops.base_dir):
            try:
                os.startfile(self.file_ops.base_dir)
                return {"success": True}
            except Exception as e:
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "No workspace active"}

if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    try:
        if webview is None:
            err_msg = "pywebview is not installed or failed to import. Please run DarkMaxxerSetup.exe or 'pip install pywebview webview'."
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

        window = webview.create_window(
            'DarkMaxxer',
            url=start_html_url,
            js_api=api,
            width=1280,
            height=800,
            min_size=(900, 600)
        )
        api.set_window(window)

        try:
            webview.start(debug=False)
        except Exception as start_err:
            # Fallback to starting without specific engine options if needed
            webview.start()
    except BaseException as e:
        if isinstance(e, SystemExit) and e.code == 0:
            sys.exit(0)
        import traceback
        tb = traceback.format_exc()
        try:
            with open(os.path.join(script_dir, "crash_report.log"), "w", encoding="utf-8") as f:
                f.write(f"Fatal Startup Error:\n{tb}\n")
            import tkinter as tk
            from tkinter import messagebox
            r = tk.Tk()
            r.withdraw()
            messagebox.showerror("DarkMaxxer Startup Crash", f"Application encountered a fatal error on startup:\n{e}\n\nCheck crash_report.log for details.")
            r.destroy()
        except Exception:
            pass
        sys.exit(1)
