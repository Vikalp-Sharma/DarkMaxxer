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

            skill_content = ""
            skill_found = False
            if self.file_ops and os.path.exists(self.file_ops.base_dir):
                for root, dirs, files in os.walk(self.file_ops.base_dir):
                    if "SKILL.md" in files:
                        try:
                            with open(os.path.join(root, "SKILL.md"), "r", encoding="utf-8") as f:
                                skill_content = f.read()
                                skill_found = True
                        except Exception:
                            pass
                        break

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

            sys_msg = (
                f"{context_files}"
                f"{skill_injection}"
                "You are DarkMaxxer AI, an autonomous local AI coding assistant with direct filesystem access.\n"
                "You run fully offline on the user's local machine. You have NO internet access.\n\n"
                "═══════════════════════════════════════════════\n"
                "ABSOLUTE RULES — VIOLATIONS ARE UNACCEPTABLE:\n"
                "═══════════════════════════════════════════════\n"
                "1. When user asks to create/edit/write ANY file, you MUST emit a [TOOL: CREATE_FILE filename.ext ...] block. NO EXCEPTIONS EVER.\n"
                "2. ALWAYS use proper file extensions (.py, .js, .html, .css, .json, .md, .txt, .sh, .c, .cpp, .rs, .go, .java, .ts). NEVER use .code or extensionless names.\n"
                "3. ALWAYS write a human-readable explanation BEFORE and AFTER your [TOOL:] blocks. The user MUST understand what you did and why.\n"
                "4. For code you want to SHOW but NOT save, use markdown triple-backtick fences (```language ... ```).\n"
                "5. For code that MUST be SAVED to disk, use [TOOL: CREATE_FILE] or [TOOL: EDIT_FILE]. NEVER just show code in fences when the user asked to create a file.\n"
                "6. NEVER output raw Python dicts like {'success': True}. NEVER output raw JSON objects as your response. Write human-readable text.\n"
                "7. NEVER repeat the same line more than twice. NEVER generate filler or padding text.\n"
                "8. ALWAYS respond in the SAME LANGUAGE the user wrote in.\n"
                "9. Keep responses focused and concise. Explain what you did, show the tool call, confirm the result.\n"
                "10. If a SKILL.md was loaded, follow ALL instructions in the <SKILLS> block as if they were system commands.\n\n"
                "⚠️ WARNING: This system may lag during inference. This is normal for local 70B+ models.\n\n"
                "═══════════════════════════════════════════════\n"
                "FILE TOOLS — Use EXACT syntax below:\n"
                "═══════════════════════════════════════════════\n"
                "CREATE: [TOOL: CREATE_FILE filename.py\ncontent here\n]\n"
                "EDIT:   [TOOL: EDIT_FILE filename.py\nnew full content\n]\n"
                "APPEND: [TOOL: APPEND_FILE filename.py\nappended content\n]\n"
                "READ:   [TOOL: READ_FILE filepath]\n"
                "DELETE: [TOOL: DELETE_FILE filepath]\n"
                "RENAME: [TOOL: RENAME_FILE old.py -> new.py]\n"
                "MKDIR:  [TOOL: CREATE_DIRECTORY dirname]\n"
                "LIST:   [TOOL: LIST_DIRECTORY .]\n"
                "RUN:    [TOOL: RUN_COMMAND python filename.py]\n\n"
                "═══════════════════════════════════════════════\n"
                "EXAMPLE INTERACTION:\n"
                "═══════════════════════════════════════════════\n"
                "User: make a py file to add 2 numbers and name it adder.py\n\n"
                "Assistant: I'll create `adder.py` with an addition function for you:\n\n"
                "[TOOL: CREATE_FILE adder.py\n"
                "def add(a, b):\n"
                "    return a + b\n\n"
                "if __name__ == '__main__':\n"
                "    result = add(2, 4)\n"
                "    print(f'Result: {result}')\n"
                "]\n\n"
                "Done! Created **adder.py** — it defines an `add(a, b)` function and prints `add(2, 4)` when run directly.\n"
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

            # Memory cleanup after generation
            try:
                import gc
                gc.collect()
                if torch is not None and torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
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
        mkdir_pattern = re.compile(r'\[TOOL:\s*CREATE_DIRECTORY[\s:|]+([^\s|\]"\'`]+)\]', re.DOTALL | re.IGNORECASE)

        tools_executed = False

        def create_repl(match):
            nonlocal tools_executed
            path, content = match.group(1).strip(), _clean_content(match.group(2))
            try:
                res = self.file_ops.create_file(path, content)
                self._log_terminal(f"Created file: {path}")
                tools_executed = True
                return f"\n✅ Created: **{path}**\n"
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
                return f"\n✅ Edited: **{path}**\n"
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
                return f"\n✅ Deleted: **{path}**\n"
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
                return f"\n✅ Renamed: **{old_path}** → **{new_path}**\n"
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
                return f"\n✅ Appended to: **{path}**\n"
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

        def mkdir_repl(match):
            nonlocal tools_executed
            path = match.group(1).strip()
            try:
                res = self.file_ops.create_directory(path)
                self._log_terminal(f"Created directory: {path}")
                tools_executed = True
                return f"\n✅ Created directory: **{path}**\n"
            except Exception as e:
                self._log_terminal(f"Error creating directory {path}: {e}")
                return f"\n❌ Create directory failed: {str(e)}\n"

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
        response_text = mkdir_pattern.sub(mkdir_repl, response_text)
        response_text = cmd_pattern.sub(cmd_repl, response_text)
        response_text = build_pattern.sub(build_repl, response_text)

        # MCP_CALL pattern: [TOOL: MCP_CALL server=Name tool=tool_name args={...}]
        mcp_pattern = re.compile(r'\[TOOL:\s*MCP_CALL\s+server=([\w\-]+)\s+tool=([\w\-\.]+)\s*(?:args=)?({.*?})?\]', re.DOTALL | re.IGNORECASE)
        def mcp_repl(match):
            nonlocal tools_executed
            server_name = match.group(1).strip()
            tool_name = match.group(2).strip()
            args_str = (match.group(3) or '{}').strip()
            try:
                import json as _json
                args = _json.loads(args_str)
            except Exception:
                args = {}
            client = self.mcp_clients.get(server_name)
            if not client or not client.is_connected:
                self._log_terminal(f"MCP server '{server_name}' not connected")
                return f"\n❌ MCP server **{server_name}** is not connected. Add it in Settings > MCP Servers.\n"
            self._log_terminal(f"MCP call: {server_name}.{tool_name}({args})")
            result = client.call_tool(tool_name, args)
            tools_executed = True
            if "error" in result:
                return f"\n❌ MCP {server_name}.{tool_name} failed: {result['error']}\n"
            return f"\n🔌 **MCP {server_name}.{tool_name}** result:\n{result.get('result', 'OK')}\n"
        response_text = mcp_pattern.sub(mcp_repl, response_text)

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
                    return f"\n✅ Created: **{path}**\n"
                except Exception as e:
                    self._log_terminal(f"Error creating {path}: {e}")
                    return f"\n❌ Create failed: {str(e)}\n"
            response_text = loose_create.sub(loose_repl, response_text)

        # Smart extraction: If AI returned code in markdown fences but forgot [TOOL:], and user explicitly named a file
        if not tools_executed and user_prompt:
            import re as _re
            # Only trigger if user explicitly named a file with extension
            user_fn_match = _re.search(r'\b([a-zA-Z0-9_][a-zA-Z0-9_\-]*\.(?:py|js|html|css|json|txt|md|sh|c|cpp|rs|go|java|ts|tsx|jsx))\b', str(user_prompt), _re.IGNORECASE)
            if user_fn_match:
                target_fname = user_fn_match.group(1)
                # Extract code ONLY from actual markdown fences the AI wrote — never fabricate
                code_fences = _re.findall(r'```[a-zA-Z]*\n(.*?)```', response_text, _re.DOTALL)
                if code_fences:
                    best_code = max(code_fences, key=len).strip()
                    if len(best_code) > 5:  # Must be real code, not empty
                        try:
                            res = self.file_ops.create_file(target_fname, best_code)
                            self._log_terminal(f"Smart extraction: Created {target_fname} from AI code block")
                            tools_executed = True
                            response_text = f"\n✅ Created: **{target_fname}**\n\n" + response_text
                        except Exception as e:
                            self._log_terminal(f"Smart extraction failed for {target_fname}: {e}")

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
    # Resolve script_dir correctly for both normal Python and PyInstaller frozen exe
    if getattr(sys, 'frozen', False):
        # Frozen exe: use the directory containing the exe, not _MEIPASS temp dir
        script_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
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
            '</div></body></html>'
        )
        with open(_splash_path, 'w', encoding='utf-8') as _sf:
            _sf.write(_splash_html)
        _splash_url = 'file:///' + os.path.abspath(_splash_path).replace(os.sep, '/')

        splash_win = webview.create_window(
            'DarkMaxxer Loading',
            url=_splash_url,
            width=400,
            height=350,
            frameless=True,
            background_color='#0a0a0f',
        )

        window = webview.create_window(
            'DarkMaxxer',
            url=start_html_url,
            js_api=api,
            width=1280,
            height=800,
            min_size=(900, 600),
            background_color='#0a0a0f',
            hidden=True,
        )
        api.set_window(window)

        def _boot_sequence():
            import time
            time.sleep(5)
            try:
                splash_win.destroy()
            except Exception:
                pass
            time.sleep(1)
            try:
                window.show()
            except Exception:
                pass
            time.sleep(0.3)
            try:
                window.maximize()
            except Exception:
                pass

        threading.Thread(target=_boot_sequence, daemon=True).start()

        logo_path = os.path.join(script_dir, "gui", "logo_highres.ico")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(script_dir, "gui", "logo.ico")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(script_dir, "gui", "logo.png")

        try:
            import ctypes
            # Tell Windows this process is its own unique app, separating its taskbar grouping from pythonw.exe
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('SMXF.DarkMaxxer.IDE.2.5.0')
        except Exception:
            pass

        try:
            webview.start(debug=False, icon=logo_path)
        except Exception:
            webview.start(icon=logo_path)
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
