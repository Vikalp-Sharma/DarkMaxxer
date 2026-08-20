# [Vikalp Sharma] - Proprietary / Anti-Theft Watermark
import os
import sys
import json
import uuid
import shutil
import threading

def _get_locallow_root():
    appdata = os.getenv('APPDATA')
    if appdata:
        return os.path.join(os.path.dirname(appdata), "LocalLow")
    return os.getenv('XDG_CONFIG_HOME', os.path.join(os.path.expanduser("~"), ".config"))

_locallow = _get_locallow_root()
_root_dir = os.path.join(_locallow, "DarkMaxxer")
os.makedirs(_root_dir, exist_ok=True)

# Remove legacy UNC folder if present, do not create UNC
_unc_path = os.path.join(_root_dir, "UNC")
if os.path.exists(_unc_path):
    try:
        shutil.rmtree(_unc_path, ignore_errors=True)
    except Exception:
        pass

_cache_dir = os.path.join(_root_dir, "Cache")
os.makedirs(_cache_dir, exist_ok=True)

# Auto-migrate legacy cache folders if present
appdata = os.getenv('APPDATA')
if appdata:
    for _old_cache_path in [
        os.path.join(appdata, "DarkMaxxer", "UNC"),
        os.path.join(appdata, "DarkMaxxer", "cache")
    ]:
        if os.path.exists(_old_cache_path) and os.path.abspath(_old_cache_path) != os.path.abspath(_cache_dir):
            try:
                for _item in os.listdir(_old_cache_path):
                    _s = os.path.join(_old_cache_path, _item)
                    _d = os.path.join(_cache_dir, _item)
                    if not os.path.exists(_d):
                        if os.path.isdir(_s):
                            shutil.copytree(_s, _d)
                        else:
                            shutil.copy2(_s, _d)
                shutil.rmtree(_old_cache_path, ignore_errors=True)
            except Exception:
                pass

os.environ["HF_HOME"] = _cache_dir
os.environ["HF_HUB_CACHE"] = os.path.join(_cache_dir, "hub")
os.environ["TORCH_HOME"] = os.path.join(_cache_dir, "torch")
os.environ["TRANSFORMERS_CACHE"] = os.path.join(_cache_dir, "transformers")
os.environ["AIRLLM_CACHE_DIR"] = _cache_dir

# Force fully offline mode — prevents SSL cert errors and network hangs in bundled exe
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

# Fix SSL certificate bundle for PyInstaller frozen environments
# Without this, torch/transformers/urllib3 raise ssl.SSLCertVerificationError
try:
    import certifi
    _ca_bundle = certifi.where()
    os.environ.setdefault("SSL_CERT_FILE", _ca_bundle)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", _ca_bundle)
    os.environ.setdefault("CURL_CA_BUNDLE", _ca_bundle)
except ImportError:
    # certifi not installed — disable SSL verification as last resort for bundled exe
    if getattr(sys, 'frozen', False):
        import ssl
        try:
            ssl._create_default_https_context = ssl._create_unverified_context
        except Exception:
            pass
        os.environ["PYTHONHTTPSVERIFY"] = "0"

# Vikalp Sharma
# Proprietary License - Do not redistribute without permission.

class MemoryManager:
    def __init__(self):
        self._lock = threading.Lock()
        self.base_dir = _root_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.minds_dir = os.path.join(self.base_dir, "Chat")
        self.context_dir = os.path.join(self.base_dir, "Context")
        
        os.makedirs(self.minds_dir, exist_ok=True)
        os.makedirs(self.context_dir, exist_ok=True)
        
        # Remove UNC if created by old init
        _unc = os.path.join(self.base_dir, "UNC")
        if os.path.exists(_unc):
            shutil.rmtree(_unc, ignore_errors=True)

        # Auto-migrate legacy chat data from previous APPDATA paths
        appdata = os.getenv('APPDATA', '')
        legacy_sources = [
            os.path.join(appdata, "DarkMaxxer", "DarkData"),
            os.path.join(appdata, "DarkMaxxer"),
            os.path.join(appdata, ".DarkMaxxer")
        ]
        for src_root in legacy_sources:
            if not src_root or not os.path.exists(src_root):
                continue
            # Migrate Minds / Chat
            for old_name in ["Minds", "Chat"]:
                old_sub = os.path.join(src_root, old_name)
                if os.path.exists(old_sub) and os.path.abspath(old_sub) != os.path.abspath(self.minds_dir):
                    try:
                        for item in os.listdir(old_sub):
                            s = os.path.join(old_sub, item)
                            d = os.path.join(self.minds_dir, item)
                            if not os.path.exists(d):
                                if os.path.isdir(s):
                                    shutil.copytree(s, d)
                                else:
                                    shutil.copy2(s, d)
                        shutil.rmtree(old_sub, ignore_errors=True)
                    except Exception:
                        pass
            # Migrate Context
            old_context = os.path.join(src_root, "Context")
            if os.path.exists(old_context) and os.path.abspath(old_context) != os.path.abspath(self.context_dir):
                try:
                    for item in os.listdir(old_context):
                        s = os.path.join(old_context, item)
                        d = os.path.join(self.context_dir, item)
                        if not os.path.exists(d):
                            if os.path.isdir(s):
                                shutil.copytree(s, d)
                            else:
                                shutil.copy2(s, d)
                    shutil.rmtree(old_context, ignore_errors=True)
                except Exception:
                    pass

    def get_workspace_dir(self, conv_id: str) -> str:
        return os.path.join(self.minds_dir, conv_id)

    def get_context_file(self, conv_id: str) -> str:
        return os.path.join(self.context_dir, f"{conv_id}.json")

    def create_conversation(self, name: str) -> str:
        with self._lock:
            conv_id = str(uuid.uuid4())
            ws_dir = self.get_workspace_dir(conv_id)
            os.makedirs(ws_dir, exist_ok=True)
            
            conv_data = {
                "id": conv_id,
                "name": name,
                "history": []
            }
            
            _tmp = self.get_context_file(conv_id) + ".tmp"
            with open(_tmp, "w", encoding="utf-8") as f:
                json.dump(conv_data, f, indent=2)
            os.replace(_tmp, self.get_context_file(conv_id))
                
            # Also create legacy directory structure for double backward-compatibility
            c_dir = os.path.join(self.context_dir, conv_id)
            os.makedirs(c_dir, exist_ok=True)
            try:
                with open(os.path.join(c_dir, "metadata.json"), "w", encoding="utf-8") as f:
                    json.dump({"id": conv_id, "name": name}, f)
                with open(os.path.join(c_dir, "history.json"), "w", encoding="utf-8") as f:
                    json.dump([], f)
            except Exception:
                pass
                
            return conv_id

    def list_conversations(self) -> list:
        with self._lock:
            conversations = []
            seen_ids = set()
            if not os.path.exists(self.context_dir):
                return conversations
                
            items = os.listdir(self.context_dir)
            for item in sorted(items, key=lambda x: not x.endswith(".json")):
                item_path = os.path.join(self.context_dir, item)
                if item.endswith(".json"):
                    try:
                        with open(item_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if "id" in data and data["id"] not in seen_ids:
                                seen_ids.add(data["id"])
                                conversations.append({
                                    "id": data["id"],
                                    "name": data.get("name", "Untitled Conversation")
                                })
                    except Exception:
                        pass
                elif os.path.isdir(item_path):
                    meta_path = os.path.join(item_path, "metadata.json")
                    if os.path.exists(meta_path):
                        try:
                            with open(meta_path, "r", encoding="utf-8") as f:
                                meta = json.load(f)
                                if "id" in meta and meta["id"] not in seen_ids:
                                    seen_ids.add(meta["id"])
                                    conversations.append({
                                        "id": meta["id"],
                                        "name": meta.get("name", "Untitled Conversation")
                                    })
                        except Exception:
                            pass
            return conversations

    def get_conversation_data(self, conv_id: str) -> dict:
        if not conv_id: return {}
        with self._lock:
            file_path = self.get_context_file(conv_id)
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
            return {}

    def set_conversation_data(self, conv_id: str, key: str, value):
        if not conv_id: return
        with self._lock:
            file_path = self.get_context_file(conv_id)
            data = {}
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    pass
            data[key] = value
            data["id"] = data.get("id", conv_id)
            try:
                _tmp = file_path + ".tmp"
                with open(_tmp, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                os.replace(_tmp, file_path)
            except Exception:
                pass

    def get_history(self, conv_id: str) -> list:
        if not conv_id:
            return []
        with self._lock:
            file_path = self.get_context_file(conv_id)
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return data.get("history", [])
                except Exception:
                    pass
            hist_path = os.path.join(self.context_dir, conv_id, "history.json")
            if os.path.exists(hist_path):
                try:
                    with open(hist_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
            return []

    def save_history(self, conv_id: str, history: list):
        if not conv_id:
            return
        with self._lock:
            file_path = self.get_context_file(conv_id)
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {"id": conv_id, "name": "DarkMaxxer Session", "history": []}
            else:
                data = {"id": conv_id, "name": "DarkMaxxer Session", "history": []}
            data["history"] = history
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception:
                pass

            # Also sync to legacy folder structure
            c_dir = os.path.join(self.context_dir, conv_id)
            os.makedirs(c_dir, exist_ok=True)
            try:
                with open(os.path.join(c_dir, "history.json"), "w", encoding="utf-8") as f:
                    json.dump(history, f, indent=2)
            except Exception:
                pass

    def delete_history(self, conv_id: str):
        self.save_history(conv_id, [])

    def rename_conversation(self, conv_id: str, new_name: str) -> bool:
        with self._lock:
            file_path = self.get_context_file(conv_id)
            if not os.path.exists(file_path):
                return False
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["name"] = new_name
                _tmp = file_path + ".tmp"
                with open(_tmp, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                os.replace(_tmp, file_path)
                
                meta_path = os.path.join(self.context_dir, conv_id, "metadata.json")
                if os.path.exists(meta_path):
                    with open(meta_path, "r", encoding="utf-8") as mf:
                        mdata = json.load(mf)
                    mdata["name"] = new_name
                    _mtmp = meta_path + ".tmp"
                    with open(_mtmp, "w", encoding="utf-8") as mf:
                        json.dump(mdata, mf)
                    os.replace(_mtmp, meta_path)
                    
                return True
            except Exception:
                return False

    def delete_conversation(self, conv_id: str):
        with self._lock:
            file_path = self.get_context_file(conv_id)
            if os.path.exists(file_path):
                os.remove(file_path)
                
            c_dir = os.path.join(self.context_dir, conv_id)
            if os.path.exists(c_dir):
                shutil.rmtree(c_dir, ignore_errors=True)
                
            ws_dir = self.get_workspace_dir(conv_id)
            if os.path.exists(ws_dir):
                shutil.rmtree(ws_dir, ignore_errors=True)


class ConfigManager:
    def __init__(self):
        self._lock = threading.Lock()
        self.base_dir = _root_dir
        self.config_path = os.path.join(self.base_dir, "config.json")
        
        # Auto-migrate config.json from locallow or previous paths into main root folder
        appdata = os.getenv('APPDATA', '')
        legacy_configs = [
            os.path.join(_root_dir, "config.json"),
            os.path.join(appdata, "DarkMaxxer", "DarkData", "config.json"),
            os.path.join(appdata, "DarkMaxxer", "config.json"),
            os.path.join(appdata, ".DarkMaxxer", "config.json")
        ]
        for old_cfg in legacy_configs:
            if old_cfg and os.path.exists(old_cfg) and os.path.abspath(old_cfg) != os.path.abspath(self.config_path):
                if not os.path.exists(self.config_path):
                    try:
                        shutil.copy2(old_cfg, self.config_path)
                    except Exception:
                        pass
                try:
                    os.remove(old_cfg)
                except Exception:
                    pass

        self._ensure_config()

    def _ensure_config(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        if not os.path.exists(self.config_path):
            default_config = self._get_default_config()
            self._save(default_config)

    def _get_default_config(self):
        return {
            "active_conv_id": None,
            "active_workspace_dir": None,
            "ai_path": None,
            "active_sidebar_tab": "chats",
            "settings": {
                "local_inference": True,
                "gpu_acceleration": True,
                "context_memory": True
            }
        }

    def _load(self):
        with self._lock:
            try:
                if os.path.exists(self.config_path):
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            if "settings" not in data or not isinstance(data["settings"], dict):
                                data["settings"] = self._get_default_config()["settings"]
                            return data
                return self._get_default_config()
            except Exception:
                return self._get_default_config()

    def _save(self, data):
        with self._lock:
            try:
                temp_path = self.config_path + ".tmp"
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                if os.path.exists(temp_path):
                    os.replace(temp_path, self.config_path)
            except Exception:
                pass

    def get_config(self):
        return self._load()

    def update_config(self, key, value):
        data = self._load()
        data[key] = value
        self._save(data)
        
    def get_settings(self):
        return self._load().get("settings", {
            "local_inference": True,
            "gpu_acceleration": True,
            "context_memory": True
        })
        
    def update_settings(self, settings_dict):
        data = self._load()
        if "settings" not in data or not isinstance(data["settings"], dict):
            data["settings"] = {}
        data["settings"].update(settings_dict)
        self._save(data)
