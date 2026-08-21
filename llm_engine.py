# [Vikalp Sharma] - Proprietary / Anti-Theft Watermark
import sys, os
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

try:
    import torch
except Exception:
    torch = None

# Fix SSL certificate errors in frozen/bundled PyInstaller environments
# torch.hub, urllib3, and transformers all need valid cert paths
if getattr(sys, 'frozen', False):
    # Ensure offline mode is set (backup — memory_manager.py sets this too)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("TORCH_HOME", os.path.join(os.getenv("APPDATA", ""), "DarkMaxxer", "Cache", "torch"))
    # Disable torch.hub network calls
    try:
        if torch is not None:
            torch.hub._validate_not_a_forked_repo = lambda *args, **kwargs: True
    except Exception:
        pass
    # SSL cert fallback
    if "SSL_CERT_FILE" not in os.environ:
        try:
            import certifi
            _ca = certifi.where()
            os.environ["SSL_CERT_FILE"] = _ca
            os.environ["REQUESTS_CA_BUNDLE"] = _ca
        except ImportError:
            import ssl
            try:
                ssl._create_default_https_context = ssl._create_unverified_context
            except Exception:
                pass

# Fix PyTorch 2.6+ breaking change: weights_only defaults to True, crashing AirLLM
if torch is not None:
    _original_torch_load = torch.load
    def _patched_torch_load(*args, **kwargs):
        if 'weights_only' not in kwargs:
            kwargs['weights_only'] = False
        return _original_torch_load(*args, **kwargs)
    torch.load = _patched_torch_load

try:
    from airllm import AutoModel
except Exception:
    AutoModel = None

import threading

# Vikalp Sharma
# Proprietary License - Do not redistribute without permission.

class LLMEngine:
    def __init__(self):
        self.model = None
        self._cached_tokenizer = None
        self.current_model_id = None
        self.model_path = None
        self._lock = threading.Lock()
        self._cancel_requested = False

    def _get_device(self):
        """Detect best available compute device: cuda (NVIDIA), rocm (AMD via PyTorch), or cpu."""
        if torch is None:
            return "cpu"
        # AMD ROCm: PyTorch ROCm build uses torch.cuda API but torch.version.hip is set
        if hasattr(torch.version, 'hip') and torch.version.hip is not None:
            if torch.cuda.is_available():  # ROCm uses CUDA API
                return "cuda"  # ROCm devices use 'cuda' device string in PyTorch
        # NVIDIA CUDA
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def _empty_cache(self):
        """Clear GPU memory cache for CUDA or ROCm."""
        if torch is not None and torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass

    def cancel(self):
        self._cancel_requested = True

    def check_compatibility(self, model_id: str) -> bool:
        """
        Always return True. The GPU limiter was removed at startup per user request.
        AirLLM will attempt to run on CPU/Metal if CUDA is unavailable or insufficient.
        """
        return True

    def download_model(self, model_id: str, hf_token: str = None, callback=None):
        """Remote model downloading is strictly disabled per user requirement for local-only models."""
        raise RuntimeError("Downloading models from remote repositories (e.g. HuggingFace) is disabled. Please provide a local model folder or weight file on disk.")

    def load_model(self, model_id: str, hf_token: str = None, callback=None):
        """Loads the model via AirLLM, GGUF/Ollama, Transformers, or PyTorch directly from local disk."""
        with self._lock:
            if self.current_model_id == model_id and self.model is not None:
                return  # Already loaded
            
            import os
            if not os.path.exists(model_id):
                raise ValueError(f"Local model folder or file not found: '{model_id}'. Remote model downloading has been disabled per strict offline security policy.")

            if callback:
                callback(f"[1/5] Resolving model path: {model_id}...")
                callback(f"[1/5] Model size: {os.path.getsize(model_id) / (1024**3):.2f} GB" if os.path.isfile(model_id) else f"[1/5] Model directory detected")
                
            if hf_token:
                os.environ["HF_TOKEN"] = hf_token

            air_err = None
            trans_err = None
            gguf_err = None
            pytorch_err = None

            # 1. Resolve Ollama Manifest / Blob / GGUF paths
            resolved_gguf_path = None
            if os.path.isfile(model_id):
                if model_id.lower().endswith(".gguf") or "sha256-" in os.path.basename(model_id):
                    resolved_gguf_path = model_id
                else:
                    # Check if file contains Ollama JSON manifest
                    try:
                        import json
                        with open(model_id, "r", encoding="utf-8") as mf:
                            data = json.load(mf)
                            if isinstance(data, dict) and "layers" in data:
                                for layer in data.get("layers", []):
                                    if layer.get("mediaType") == "application/vnd.ollama.image.model" and "digest" in layer:
                                        digest_hash = layer["digest"].replace("sha256:", "sha256-")
                            
                                        # Walk UP the directory tree from manifest to find blob stores
                                        blob_candidates = []
                                        _sd = os.path.dirname(os.path.abspath(model_id))
                                        _seen = set()
                                        while _sd and _sd not in _seen:
                                            _seen.add(_sd)
                                            _bd = os.path.join(_sd, "blobs")
                                            if os.path.isdir(_bd):
                                                _direct = os.path.join(_bd, digest_hash)
                                                if os.path.exists(_direct):
                                                    blob_candidates.append(_direct)
                                                for _alias in [".darkmaxxer_alias", ".cache_alias"]:
                                                    _ap = os.path.join(_bd, _alias, digest_hash + ".gguf")
                                                    if os.path.exists(_ap):
                                                        blob_candidates.append(_ap)
                                            _np = os.path.dirname(_sd)
                                            if _np == _sd:
                                                break
                                            _sd = _np
                                        # Pick best: prefer .gguf extension, then largest file
                                        if blob_candidates:
                                            _gc = [c for c in blob_candidates if c.lower().endswith('.gguf')]
                                            resolved_gguf_path = max(_gc or blob_candidates, key=lambda p: os.path.getsize(p))
                                            if callback:
                                                callback(f"Resolved Ollama manifest to blob: {resolved_gguf_path} ({os.path.getsize(resolved_gguf_path):,} bytes)")
                                        break
                    except Exception:
                        pass

            # 2. Try loading GGUF / Ollama model blob via Transformers offline
            if resolved_gguf_path and os.path.exists(resolved_gguf_path):
                if callback:
                    callback(f"Loading GGUF / Ollama weight file via Transformers offline: {os.path.basename(resolved_gguf_path)}...")
                try:
                    from transformers import AutoModelForCausalLM, AutoTokenizer
                    import torch
                    
                    target_path = resolved_gguf_path
                    if not target_path.lower().endswith(".gguf"):
                        # On Linux, Ollama blobs don't have .gguf extension.
                        # Look for existing .gguf alias next to the blob first.
                        blob_dir = os.path.dirname(resolved_gguf_path)
                        blob_name = os.path.basename(resolved_gguf_path)
                        alias_candidates = [
                            os.path.join(blob_dir, ".darkmaxxer_alias", blob_name + ".gguf"),
                            os.path.join(blob_dir, ".cache_alias", blob_name + ".gguf"),
                        ]
                        found_alias = None
                        for ac in alias_candidates:
                            if os.path.exists(ac):
                                found_alias = ac
                                break
                        
                        if found_alias:
                            target_path = found_alias
                        else:
                            # Create a .gguf symlink so Transformers recognizes it
                            alias_dir = os.path.join(blob_dir, ".darkmaxxer_alias")
                            os.makedirs(alias_dir, exist_ok=True)
                            target_path = os.path.join(alias_dir, blob_name + ".gguf")
                            if not os.path.exists(target_path):
                                if callback:
                                    callback("Creating .gguf alias link for Transformers...")
                                try:
                                    os.symlink(resolved_gguf_path, target_path)
                                except OSError:
                                    try:
                                        os.link(resolved_gguf_path, target_path)
                                    except OSError:
                                        target_path = resolved_gguf_path

                    gguf_dir = os.path.dirname(target_path)
                    gguf_filename = os.path.basename(target_path)
                    
                    # Set up offload folder to prevent device_map failures
                    offload_dir = os.path.join(os.path.expanduser("~"), ".darkmaxxer_build", "offload")
                    os.makedirs(offload_dir, exist_ok=True)
                    
                    if callback:
                        callback(f"Loading GGUF model: {gguf_filename}...")
                    
                    self.model = AutoModelForCausalLM.from_pretrained(
                        gguf_dir,
                        gguf_file=gguf_filename,
                        device_map="auto",
                        torch_dtype=torch.float16,
                        low_cpu_mem_usage=True,
                        offload_folder=offload_dir,
                        local_files_only=True
                    )
                    self.loaded_gguf_path = target_path
                    self.current_model_id = model_id
                    self.model_path = model_id
                    self.model_type = "gguf"
                    
                    # Try to load tokenizer from the GGUF file
                    try:
                        tok = AutoTokenizer.from_pretrained(
                            gguf_dir, gguf_file=gguf_filename, local_files_only=True
                        )
                        self.model.tokenizer = tok
                        self._cached_tokenizer = tok
                    except Exception:
                        pass
                    
                    if callback:
                        callback("GGUF model loaded successfully -> Ready for User.")
                    try:
                        import gc; gc.collect()
                        self._empty_cache()
                    except Exception:
                        pass
                    return
                except Exception as e:
                    gguf_err = str(e)
                    if callback:
                        callback(f"GGUF/Ollama load check passed to next engine ({gguf_err[:100]})...")

            # 3. Try loading strictly through AirLLM Layer-Wise Offloading Engine
            try:
                target_air_path = None
                if os.path.isdir(model_id):
                    if os.path.exists(os.path.join(model_id, "config.json")):
                        target_air_path = model_id
                elif os.path.isfile(model_id):
                    parent_dir = os.path.dirname(model_id)
                    if os.path.exists(os.path.join(parent_dir, "config.json")):
                        target_air_path = parent_dir
                # If we resolved a GGUF blob, check its parent for config.json
                if target_air_path is None and resolved_gguf_path and os.path.exists(resolved_gguf_path):
                    _gp = os.path.dirname(resolved_gguf_path)
                    if os.path.exists(os.path.join(_gp, "config.json")):
                        target_air_path = _gp
                if target_air_path is None:
                    raise ValueError(f"AirLLM requires a local directory with config.json and safetensors/bin/pth weights. No compatible directory found for '{os.path.basename(model_id)}'.")
                if callback:
                    callback(f"Routing through AirLLM Layer-Wise Engine: {target_air_path}...")
                    callback("[3/5] Initializing layer-wise GPU offloading (this loads one layer at a time)...")
                    callback("⚠️ This may take a while and the app might lag — this is normal for large models.")
                _AirAutoModel = AutoModel
                if _AirAutoModel is None:
                    from airllm import AutoModel as _AirAutoModel
                self.model = _AirAutoModel.from_pretrained(target_air_path)
                try:
                    setattr(self.model, 'is_airllm', True)
                except Exception:
                    pass
                self.current_model_id = model_id
                self.model_path = model_id
                if callback:
                    callback("AirLLM Layer-Wise Offloading active -> Model loaded and ready for User.")
                try:
                    import gc; gc.collect()
                    import torch
                    self._empty_cache()
                except: pass
                return
            except Exception as e:
                air_err = str(e)
                if callback:
                    callback(f"AirLLM direct load check passed ({air_err[:100]})...")

            # 4. Try loading as direct PyTorch / Pickle (.file, .pkl, .pth, .pt, .bin)
            if os.path.isfile(model_id):
                try:
                    import torch
                    import pickle
                    if callback:
                        callback(f"Attempting to load weight/file object: {model_id}")
                    loaded_obj = None
                    try:
                        loaded_obj = torch.load(model_id, map_location="cpu", weights_only=False)
                    except Exception:
                        pass
                    
                    if loaded_obj is not None and (hasattr(loaded_obj, "generate") or hasattr(loaded_obj, "forward") or hasattr(loaded_obj, "tokenizer") or callable(loaded_obj)):
                        self.model = loaded_obj
                        self.current_model_id = model_id
                        self.model_path = model_id
                        if callback:
                            callback("Model file loaded through PyTorch engine -> Ready for User.")
                        try:
                            import gc; gc.collect()
                            import torch
                            self._empty_cache()
                        except: pass
                        return
                except Exception as e:
                    pytorch_err = str(e)

            # 5. Fallback try transformers AutoModelForCausalLM directly offline/local
            try:
                from transformers import AutoModelForCausalLM, AutoTokenizer
                if os.path.isfile(model_id):
                    parent_dir = os.path.dirname(model_id)
                    if os.path.exists(os.path.join(parent_dir, "config.json")):
                        target_path = parent_dir
                    else:
                        ext = os.path.splitext(model_id.lower())[1]
                        if ext in ['.safetensors', '.bin', '.pt', '.pth']:
                            raise ValueError(f"Unlike GGUF files, standalone '{ext}' files do not contain architecture metadata. You MUST have the model's 'config.json' file in the same folder ({parent_dir}/) to load it.")
                        elif ext == '.onnx':
                            raise ValueError(f"To load an ONNX model, you MUST have the model's 'config.json' file in the same folder ({parent_dir}/).")
                        else:
                            raise ValueError("Transformers fallback requires a HuggingFace Hub ID or a local directory containing config.json.")
                else:
                    target_path = model_id
                if callback:
                    callback(f"Attempting fallback load via transformers from {target_path}...")
                is_local = os.path.exists(target_path)
                try:
                    self.model = AutoModelForCausalLM.from_pretrained(target_path, local_files_only=is_local, device_map="auto", low_cpu_mem_usage=True)
                except Exception:
                    self.model = AutoModelForCausalLM.from_pretrained(target_path, device_map="auto", low_cpu_mem_usage=True)
                try:
                    self.model.tokenizer = AutoTokenizer.from_pretrained(target_path, local_files_only=is_local)
                except Exception:
                    pass
                self.current_model_id = model_id
                self.model_path = model_id
                if callback:
                    callback("Transformers fallback active -> Model ready for User.")
                try:
                    import gc; gc.collect()
                    import torch
                    self._empty_cache()
                except: pass
                return
            except Exception as e:
                trans_err = str(e)
                if callback:
                    callback(f"Transformers fallback check failed ({trans_err[:100]})...")

            # 6. If all failed, construct detailed error report without unbound variables
            err_msg = f"Could not load model '{model_id}'."
            if gguf_err:
                err_msg += f"\n- GGUF/Ollama Loader: {gguf_err[:250] + '...' if len(gguf_err) > 250 else gguf_err}"
            if air_err:
                err_msg += f"\n- AirLLM Engine: {air_err[:250] + '...' if len(air_err) > 250 else air_err}"
            if pytorch_err:
                err_msg += f"\n- PyTorch/Pickle Loader: {pytorch_err[:250] + '...' if len(pytorch_err) > 250 else pytorch_err}"
            if trans_err:
                err_msg += f"\n- Transformers Fallback: {trans_err[:250] + '...' if len(trans_err) > 250 else trans_err}"
            raise RuntimeError(err_msg)

    def cancel(self):
        """Immediately aborts any ongoing generation."""
        self._cancel_requested = True

    def generate(self, prompt: str, max_new_tokens: int = 131072, use_gpu: bool = True) -> str:
        """
        Generate text from the loaded model object (AirLLM, GGUF, Transformers, or PyTorch custom object).
        """
        if not self.model:
            raise ValueError("No model loaded.")
            
        with self._lock:
            self._cancel_requested = False
            # Resolve tokenizer offline
            tokenizer = self._cached_tokenizer
            if tokenizer is None and hasattr(self.model, "tokenizer") and self.model.tokenizer is not None:
                tokenizer = self.model.tokenizer
            elif tokenizer is None and hasattr(self.model, "get_tokenizer") and callable(self.model.get_tokenizer):
                tokenizer = self.model.get_tokenizer()
            elif tokenizer is None:
                # Attempt to find tokenizer from parent folder, GGUF file, or gpt2 fallback strictly offline
                import os
                from transformers import AutoTokenizer
                
                # If we saved the true GGUF path during load_model, use it!
                if hasattr(self, 'loaded_gguf_path') and self.loaded_gguf_path and os.path.exists(self.loaded_gguf_path):
                    try:
                        tokenizer = AutoTokenizer.from_pretrained(os.path.dirname(self.loaded_gguf_path), gguf_file=os.path.basename(self.loaded_gguf_path), local_files_only=True)
                    except Exception:
                        pass
                
                if tokenizer is None:
                    try:
                        if self.current_model_id and os.path.isfile(self.current_model_id):
                            if self.current_model_id.lower().endswith('.gguf'):
                                try:
                                    tokenizer = AutoTokenizer.from_pretrained(os.path.dirname(self.current_model_id), gguf_file=os.path.basename(self.current_model_id), local_files_only=True)
                                except Exception:
                                    pass
                            if tokenizer is None:
                                try:
                                    tokenizer = AutoTokenizer.from_pretrained(os.path.dirname(self.current_model_id), local_files_only=True)
                                except Exception:
                                    pass
                        else:
                            is_loc = self.current_model_id and os.path.exists(self.current_model_id)
                            tokenizer = AutoTokenizer.from_pretrained(self.current_model_id, local_files_only=is_loc)
                    except Exception:
                        pass
                
                if tokenizer is not None:
                    self._cached_tokenizer = tokenizer
                    try:
                        self.model.tokenizer = tokenizer
                    except Exception:
                        pass
                
                if tokenizer is None:
                    raise RuntimeError("Could not find or load a tokenizer for this model file locally. Please ensure tokenizer/config files exist alongside your model file. Aborting to prevent gibberish output.")

            if isinstance(prompt, list):
                # Guaranteed System Prompt Injection
                sys_msgs = [m.get("content", "") for m in prompt if m.get("role") == "system"]
                if sys_msgs:
                    sys_text = "\n\n".join(sys_msgs)
                    new_prompt = []
                    merged = False
                    for m in prompt:
                        if m.get("role") == "system":
                            continue
                        if m.get("role") == "user" and not merged:
                            new_prompt.append({"role": "user", "content": f"{sys_text}\n\n--- END SYSTEM INSTRUCTIONS ---\n\nUser Request:\n{m.get('content', '')}"})
                            merged = True
                        else:
                            new_prompt.append(m)
                    prompt = new_prompt

                prompt_str = ""
                if tokenizer is not None and hasattr(tokenizer, "apply_chat_template"):
                    try:
                        prompt_str = tokenizer.apply_chat_template(prompt, tokenize=False, add_generation_prompt=True)
                    except Exception:
                        prompt_str = ""
                if not prompt_str:
                    for m in prompt:
                        role = m.get("role", "user")
                        content = m.get("content", "")
                        if role == "system":
                            prompt_str += f"<|im_start|>system\n{content}<|im_end|>\n"
                        elif role == "user":
                            prompt_str += f"<|im_start|>user\n{content}<|im_end|>\n"
                        elif role == "assistant":
                            prompt_str += f"<|im_start|>assistant\n{content}<|im_end|>\n"
                    prompt_str += "<|im_start|>assistant\n"
            else:
                prompt_str = str(prompt)

            input_tokens = tokenizer(prompt_str, return_tensors="pt")
            
            # Check GPU availability
            device = self._get_device()
            if use_gpu and device != "cpu":
                input_ids = input_tokens.input_ids.to(device)
            else:
                input_ids = input_tokens.input_ids

            if input_ids.shape[1] == 0:
                raise RuntimeError("Tokenizer returned 0 tokens. This usually happens if you loaded a model weight file (.safetensors, .bin, .pth) but forgot to add 'config.json' and 'tokenizer.json' into the same folder.")

            if use_gpu and device != "cpu":
                if hasattr(self.model, "to") and not hasattr(self.model, "is_airllm"):
                    try:
                        self.model.to(device)
                    except Exception:
                        pass
            else:
                if hasattr(self.model, "to") and not hasattr(self.model, "is_airllm"):
                    try:
                        self.model.to("cpu")
                    except Exception:
                        pass
            
            # Generate response tokens
            try:
                import torch
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
            except Exception:
                pass

            if hasattr(self.model, "generate"):
                gen_kwargs = {
                    "input_ids": input_ids,
                    "max_new_tokens": max_new_tokens if max_new_tokens > 0 else 131072,
                    "use_cache": True,
                    "return_dict_in_generate": True,
                    "repetition_penalty": 1.18,
                    "do_sample": False,
                    "temperature": 0.7,
                    "top_p": 0.9,
                }
                if hasattr(tokenizer, "eos_token_id") and tokenizer.eos_token_id is not None:
                    gen_kwargs["eos_token_id"] = tokenizer.eos_token_id
                    gen_kwargs["pad_token_id"] = getattr(tokenizer, "pad_token_id", None) or tokenizer.eos_token_id
                
                try:
                    from transformers import StoppingCriteria, StoppingCriteriaList
                    class CancelGuard(StoppingCriteria):
                        def __init__(self, engine):
                            self.engine = engine
                        def __call__(self, input_ids_tensor, scores, **kwargs):
                            return getattr(self.engine, '_cancel_requested', False)
                    gen_kwargs["stopping_criteria"] = StoppingCriteriaList([CancelGuard(self)])
                except Exception:
                    pass
                
                try:
                    generation_output = self.model.generate(**gen_kwargs)
                except TypeError:
                    # Fallback if specific kwargs are rejected by custom generate methods
                    generation_output = self.model.generate(
                        input_ids,
                        max_new_tokens=max_new_tokens if max_new_tokens > 0 else 131072,
                        use_cache=True,
                        return_dict_in_generate=True
                    )
                if hasattr(generation_output, "sequences"):
                    out_tokens = generation_output.sequences[0]
                elif torch is not None and isinstance(generation_output, torch.Tensor):
                    out_tokens = generation_output[0] if generation_output.dim() > 1 else generation_output
                else:
                    out_tokens = generation_output
            elif callable(self.model):
                out_tokens = self.model(input_ids)
                if isinstance(out_tokens, tuple):
                    out_tokens = out_tokens[0]
                if hasattr(out_tokens, "logits"):
                    out_tokens = out_tokens.logits.argmax(dim=-1)[0]
            else:
                raise RuntimeError("Loaded model object does not support generate() or forward inference.")
            
            if hasattr(input_ids, "shape") and hasattr(out_tokens, "shape") and input_ids.shape[-1] < out_tokens.shape[-1]:
                gen_tokens = out_tokens[input_ids.shape[-1]:]
            else:
                gen_tokens = out_tokens
                
            output_text = tokenizer.decode(gen_tokens, skip_special_tokens=True)
            
            if isinstance(prompt, str) and output_text.startswith(prompt):
                output_text = output_text[len(prompt):]
            elif isinstance(prompt_str, str) and output_text.startswith(prompt_str):
                output_text = output_text[len(prompt_str):]
            
            output_text = output_text.strip()
            
            # Stop generation if model echoes conversation markers or special turn-end tokens
            stop_markers = [
                "\nuser:", "\nUser:", "\nassistant:", "\nAssistant:", "user:", "User:", "assistant:", "Assistant:", "Assista:", "assista:",
                "<end_of_turn>", "<|eot_id|>", "<|im_end|>", "</s>", "<|end|>", "<|endoftext|>", "<|start_header_id|>", "<|im_start|>",
                "</end_of_turn>", "<end_of_turn/>"
            ]
            for stop_marker in stop_markers:
                if stop_marker in output_text:
                    output_text = output_text.split(stop_marker)[0]
                    
            output_text = output_text.strip()
            
            # Anti-loop filter: if the model gets stuck repeating identical lines
            lines = output_text.splitlines()
            if len(lines) > 5 and len(set(lines[-10:])) == 1:
                cleaned_lines = []
                for line in lines:
                    if len(cleaned_lines) > 2 and line == cleaned_lines[-1] and line == cleaned_lines[-2]:
                        continue
                    cleaned_lines.append(line)
                output_text = "\n".join(cleaned_lines)
            
            # Anti-word repetition filter on a single line
            words = output_text.split()
            if len(words) > 15 and len(set(words[-15:])) == 1:
                cleaned_words = []
                for w in words:
                    if len(cleaned_words) > 3 and w == cleaned_words[-1] and w == cleaned_words[-2] and w == cleaned_words[-3]:
                        continue
                    cleaned_words.append(w)
                output_text = " ".join(cleaned_words)
                
            return output_text.strip()

