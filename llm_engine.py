# [Vikalp Sharma] - Proprietary / Anti-Theft Watermark
import sys, os
def _ensure_local_site_packages():
    _here = os.path.dirname(os.path.abspath(__file__))
    _cands = [
        os.path.join(_here, "venv", "Lib", "site-packages"),
        os.path.join(_here, "..", "venv", "Lib", "site-packages"),
        r"S:\DarkMaxxer\venv\Lib\site-packages",
        os.path.join(os.path.expanduser("~"), "DarkMaxxer", "venv", "Lib", "site-packages"),
        os.path.join("C:\\DarkMaxxer", "venv", "Lib", "site-packages"),
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
        self.tokenizer = None
        self.model_path = None
        self.current_model_id = None
        self._lock = threading.Lock()

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
                callback(f"Loading local model from disk: {model_id}...")
                
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
                                        home_blobs = os.path.expanduser(os.path.join("~", ".ollama", "models", "blobs", digest_hash))
                                        local_blobs = os.path.join(os.path.dirname(model_id), "..", "blobs", digest_hash)
                                        local_same = os.path.join(os.path.dirname(model_id), digest_hash)
                                        for candidate in [home_blobs, os.path.abspath(local_blobs), local_same]:
                                            if os.path.exists(candidate):
                                                resolved_gguf_path = candidate
                                                if callback:
                                                    callback(f"Resolved Ollama manifest to model blob: {candidate}")
                                                break
                                        break
                    except Exception:
                        pass

            # 2. Try loading GGUF / Ollama model blob via Transformers offline
            if resolved_gguf_path and os.path.exists(resolved_gguf_path):
                if callback:
                    callback(f"Loading GGUF / Ollama weight file via Transformers offline: {os.path.basename(resolved_gguf_path)}...")
                try:
                    from transformers import AutoModelForCausalLM, AutoTokenizer
                    
                    target_path = resolved_gguf_path
                    if not target_path.lower().endswith(".gguf"):
                        _app = os.getenv('APPDATA', '')
                        if _app and os.path.exists(os.path.dirname(_app)):
                            _locallow = os.path.join(os.path.dirname(_app), "LocalLow")
                        else:
                            _locallow = os.path.join(os.path.expanduser("~"), "AppData", "LocalLow")
                        alias_dir = os.path.join(_locallow, "DarkMaxxer", "Cache", "models_symlinks")
                        os.makedirs(alias_dir, exist_ok=True)
                        target_path = os.path.join(alias_dir, os.path.basename(resolved_gguf_path) + ".gguf")
                        if not os.path.exists(target_path):
                            if callback:
                                callback("Creating instant hard link to satisfy extension check...")
                            try:
                                os.link(resolved_gguf_path, target_path)
                            except OSError:
                                try:
                                    os.symlink(resolved_gguf_path, target_path)
                                except OSError:
                                    if callback:
                                        callback("Warning: Could not link. Trying without extension...")
                                    target_path = resolved_gguf_path

                    gguf_dir = os.path.dirname(target_path)
                    gguf_filename = os.path.basename(target_path)
                    
                    # Enforce local_files_only=True so it never makes online network requests
                    try:
                        self.model = AutoModelForCausalLM.from_pretrained(
                            gguf_dir,
                            gguf_file=gguf_filename,
                            token=hf_token,
                            local_files_only=True
                        )
                    except Exception:
                        self.model = AutoModelForCausalLM.from_pretrained(
                            gguf_dir,
                            gguf_file=gguf_filename,
                            token=hf_token
                        )
                    
                    self.loaded_gguf_path = target_path
                    try:
                        self.model.tokenizer = AutoTokenizer.from_pretrained(
                            gguf_dir,
                            gguf_file=gguf_filename,
                            token=hf_token,
                            local_files_only=True
                        )
                    except Exception:
                        try:
                            self.model.tokenizer = AutoTokenizer.from_pretrained(gguf_dir, local_files_only=True)
                        except Exception:
                            pass
                    
                    self.current_model_id = model_id
                    self.model_path = model_id
                    if callback:
                        callback("Ollama/GGUF model loaded successfully -> Ready for User.")
                    return
                except Exception as e:
                    gguf_err = str(e)
                    if callback:
                        callback(f"GGUF/Ollama load check passed to next engine ({gguf_err[:100]})...")

            # 3. Try loading strictly through AirLLM Layer-Wise Offloading Engine
            try:
                if os.path.isfile(model_id):
                    parent_dir = os.path.dirname(model_id)
                    if os.path.exists(os.path.join(parent_dir, "config.json")):
                        target_air_path = parent_dir
                    else:
                        raise ValueError("AirLLM requires a HuggingFace Hub ID or a local directory containing config.json. Bypassing AirLLM to avoid hanging.")
                else:
                    target_air_path = model_id
                if callback:
                    callback(f"Routing through AirLLM Layer-Wise Engine: {target_air_path}...")
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
                        loaded_obj = torch.load(model_id, map_location="cpu", weights_only=True)
                    except Exception:
                        pass
                    
                    if loaded_obj is not None and (hasattr(loaded_obj, "generate") or hasattr(loaded_obj, "forward") or hasattr(loaded_obj, "tokenizer") or callable(loaded_obj)):
                        self.model = loaded_obj
                        self.current_model_id = model_id
                        self.model_path = model_id
                        if callback:
                            callback("Model file loaded through PyTorch engine -> Ready for User.")
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
                        raise ValueError("Transformers fallback requires a HuggingFace Hub ID or a local directory containing config.json. Bypassing to avoid hanging.")
                else:
                    target_path = model_id
                if callback:
                    callback(f"Attempting fallback load via transformers from {target_path}...")
                is_local = os.path.exists(target_path)
                try:
                    self.model = AutoModelForCausalLM.from_pretrained(target_path, local_files_only=is_local)
                except Exception:
                    self.model = AutoModelForCausalLM.from_pretrained(target_path)
                try:
                    self.model.tokenizer = AutoTokenizer.from_pretrained(target_path, local_files_only=is_local)
                except Exception:
                    pass
                self.current_model_id = model_id
                self.model_path = model_id
                if callback:
                    callback("Transformers fallback active -> Model ready for User.")
                return
            except Exception as e:
                trans_err = str(e)
                if callback:
                    callback(f"Transformers fallback check failed ({trans_err[:100]})...")

            # 6. If all failed, construct detailed error report without unbound variables
            err_msg = f"Could not load model '{model_id}'."
            if gguf_err:
                err_msg += f"\n- GGUF/Ollama Loader: {gguf_err}"
            if air_err:
                err_msg += f"\n- AirLLM Engine: {air_err}"
            if pytorch_err:
                err_msg += f"\n- PyTorch/Pickle Loader: {pytorch_err}"
            if trans_err:
                err_msg += f"\n- Transformers Fallback: {trans_err}"
            raise RuntimeError(err_msg)

    def generate(self, prompt: str, max_new_tokens: int = 512, use_gpu: bool = True) -> str:
        """
        Generate text from the loaded model object (AirLLM, GGUF, Transformers, or PyTorch custom object).
        """
        if not self.model:
            raise ValueError("No model loaded.")
            
        with self._lock:
            # Resolve tokenizer offline
            tokenizer = None
            if hasattr(self.model, "tokenizer") and self.model.tokenizer is not None:
                tokenizer = self.model.tokenizer
            elif hasattr(self.model, "get_tokenizer") and callable(self.model.get_tokenizer):
                tokenizer = self.model.get_tokenizer()
            else:
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
                            try:
                                tokenizer = AutoTokenizer.from_pretrained(os.path.dirname(self.current_model_id), gguf_file=os.path.basename(self.current_model_id), local_files_only=True)
                            except Exception:
                                tokenizer = AutoTokenizer.from_pretrained(self.current_model_id, local_files_only=True)
                        else:
                            is_loc = self.current_model_id and os.path.exists(self.current_model_id)
                            tokenizer = AutoTokenizer.from_pretrained(self.current_model_id, local_files_only=is_loc)
                    except Exception:
                        pass
                
                if tokenizer is not None:
                    try:
                        self.model.tokenizer = tokenizer
                    except Exception:
                        pass
                
                if tokenizer is None:
                    raise RuntimeError("Could not find or load a tokenizer for this model file locally. Please ensure tokenizer/config files exist alongside your model file. Aborting to prevent gibberish output.")

            if isinstance(prompt, list):
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
            input_ids = input_tokens.input_ids
            attention_mask = input_tokens.get("attention_mask", None)
            
            # Check GPU and ensure input tensors match model device precisely
            if use_gpu and torch is not None and torch.cuda.is_available():
                if hasattr(self.model, "to") and not hasattr(self.model, "is_airllm"):
                    try:
                        self.model.to("cuda")
                    except Exception:
                        pass
                target_device = getattr(self.model, "device", None)
                if target_device is None and hasattr(self.model, "parameters"):
                    try:
                        target_device = next(self.model.parameters()).device
                    except Exception:
                        target_device = "cuda" if not hasattr(self.model, "is_airllm") else "cpu"
                if target_device is None:
                    target_device = "cuda" if not hasattr(self.model, "is_airllm") else "cpu"
                try:
                    input_ids = input_ids.to(target_device)
                    if attention_mask is not None:
                        attention_mask = attention_mask.to(target_device)
                except Exception:
                    pass
            
            # Generate response tokens
            if hasattr(self.model, "generate"):
                gen_kwargs = {
                    "input_ids": input_ids,
                    "max_new_tokens": min(max_new_tokens, 512),
                    "use_cache": True,
                    "return_dict_in_generate": True,
                    "repetition_penalty": 1.18,
                    "do_sample": True,
                    "temperature": 0.7,
                    "top_p": 0.9,
                }
                if attention_mask is not None:
                    gen_kwargs["attention_mask"] = attention_mask
                if hasattr(tokenizer, "eos_token_id") and tokenizer.eos_token_id is not None:
                    gen_kwargs["eos_token_id"] = tokenizer.eos_token_id
                    gen_kwargs["pad_token_id"] = getattr(tokenizer, "pad_token_id", None) or tokenizer.eos_token_id
                
                try:
                    generation_output = self.model.generate(**gen_kwargs)
                except TypeError:
                    # Fallback if specific kwargs are rejected by custom generate methods
                    generation_output = self.model.generate(
                        input_ids,
                        max_new_tokens=min(max_new_tokens, 512),
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

    def unload_model(self):
        """Unload any active model and free up CPU/CUDA memory safely."""
        with self._lock:
            self.model = None
            self.tokenizer = None
            self.model_path = None
            self.current_model_id = None
            if torch is not None:
                try:
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except Exception:
                    pass
            import gc
            gc.collect()
            return {"success": True}

    def _tokenize_prompt(self, prompt: str) -> list:
        """Tokenize prompt using loaded tokenizer or fallback whitespace tokenizer."""
        if self.tokenizer is not None:
            try:
                res = self.tokenizer(prompt)
                return res.get("input_ids", res) if isinstance(res, dict) else res
            except Exception:
                pass
        return prompt.split()

