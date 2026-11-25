#!/usr/bin/env python3
# [Vikalp Sharma] - Proprietary / Anti-Theft Watermark
# DarkMaxxer Universal AI Engine Daemon (JSON-RPC over Stdin/Stdout)
import sys
import os
import json
import time
import threading
import gc

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

def emit(data):
    """Emit JSON message to stdout for Rust core to consume."""
    try:
        sys.stdout.write(json.dumps(data) + "\n")
        sys.stdout.flush()
    except Exception:
        pass

class UniversalAIEngine:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.model_path = None
        self.model_type = None
        self.device = "cpu"
        self._cancel_requested = False
        self._is_generating = False
        self._lock = threading.Lock()

    def check_compatibility(self, path):
        """Check hardware and model architecture compatibility."""
        has_cuda = False
        vram_gb = 0
        device_name = "CPU"
        try:
            import torch
            has_cuda = torch.cuda.is_available()
            if has_cuda:
                vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
                device_name = torch.cuda.get_device_name(0)
        except Exception:
            pass

        if not path or not os.path.exists(path):
            return {
                "success": False,
                "compatible": False,
                "message": f"Model path not found: '{path}'",
                "cuda": has_cuda,
                "vram": vram_gb,
                "device": device_name
            }

        lower = str(path).lower()
        is_gguf = lower.endswith(".gguf")
        if not is_gguf and os.path.isfile(path):
            try:
                with open(path, "rb") as f:
                    if f.read(4) == b"GGUF":
                        is_gguf = True
            except Exception:
                pass
        is_safetensors = lower.endswith(".safetensors") or os.path.isdir(path)

        msg = f"Compatible ({device_name}). Universal loader enabled."
        if is_gguf:
            msg += " GGUF quant detected."
        elif is_safetensors:
            msg += " Safetensors/HF model detected."

        return {
            "success": True,
            "compatible": True,
            "message": msg,
            "cuda": has_cuda,
            "vram": vram_gb,
            "device": device_name
        }

    def load_model(self, model_path, use_gpu=True, compute_mode=None):
        with self._lock:
            if self.model_path == model_path and self.model is not None:
                emit({"event": "loaded", "success": True, "model_path": model_path, "device": self.device})
                return

            if self.model is not None:
                emit({"event": "status", "message": "Unloading previous model from memory..."})
                del self.model
                self.model = None
                self.tokenizer = None
                gc.collect()

            self.model_path = model_path
            self._cancel_requested = False

            def log_callback(msg):
                emit({"event": "status", "message": str(msg)})

            size_gb = (os.path.getsize(model_path) / (1024**3)) if os.path.isfile(model_path) else 10.0
            log_callback(f"Resolving model architecture: {os.path.basename(model_path)} ({size_gb:.2f} GB)...")

            lower = str(model_path).lower()
            is_gguf = lower.endswith(".gguf")
            if not is_gguf and os.path.isfile(model_path):
                try:
                    with open(model_path, "rb") as f:
                        if f.read(4) == b"GGUF":
                            is_gguf = True
                except Exception:
                    pass

            # Strategy 1: For compact GGUF models (< 2.5 GB), try Fast Direct In-Memory loading
            if is_gguf and size_gb < 2.5:
                try:
                    log_callback("Model size is compact (< 2.5GB). Initializing Fast In-Memory GGUF engine...")
                    import torch
                    from transformers import AutoTokenizer, AutoModelForCausalLM

                    gguf_dir = os.path.dirname(model_path)
                    gguf_file = os.path.basename(model_path)

                    self.tokenizer = AutoTokenizer.from_pretrained(gguf_dir, gguf_file=gguf_file)
                    if self.tokenizer.pad_token is None:
                        self.tokenizer.pad_token = self.tokenizer.eos_token

                    dev = "cuda:0" if (use_gpu and torch.cuda.is_available()) else "cpu"
                    dtype = torch.float16 if dev != "cpu" else torch.float32

                    self.model = AutoModelForCausalLM.from_pretrained(
                        gguf_dir,
                        gguf_file=gguf_file,
                        torch_dtype=dtype,
                        device_map="auto" if dev != "cpu" else None
                    )
                    if dev == "cpu":
                        self.model = self.model.to("cpu")

                    self.model_type = "fast_transformers"
                    self.device = dev
                    self.is_embedding_model = False
                    emit({"event": "loaded", "success": True, "model_path": model_path, "device": self.device})
                    log_callback("Fast In-Memory Engine loaded successfully!")
                    return
                except Exception as e_fast:
                    log_callback(f"Fast loader falling back to AirLLM: {e_fast}")

            # Strategy 2: AirLLM Layer-Wise Streaming Engine (for large GGUF models >= 2.5GB or fallback)
            if is_gguf:
                try:
                    from gguf_airllm import load_gguf_via_airllm
                    log_callback("Activating AirLLM Layer-Wise Offloading Engine (Low-RAM protection)...")
                    self.model = load_gguf_via_airllm(model_path, callback=log_callback, use_gpu=use_gpu)
                    self.tokenizer = getattr(self.model, "tokenizer", None)
                    self.model_type = "gguf_airllm"
                    self.device = getattr(self.model, "airllm_device", "cpu")
                    self.is_embedding_model = False
                    emit({"event": "loaded", "success": True, "model_path": model_path, "device": self.device})
                    return
                except Exception as e_gguf:
                    log_callback(f"AirLLM wrapper note: {e_gguf}")

            # Strategy 3: Standard Transformers / Safetensors / PyTorch Directory
            try:
                log_callback("Loading via Universal Safetensors / HuggingFace Engine...")
                import torch
                from transformers import AutoTokenizer, AutoModelForCausalLM

                model_dir = model_path if os.path.isdir(model_path) else os.path.dirname(model_path)
                config_path = os.path.join(model_dir, "config.json")

                if not os.path.exists(config_path):
                    log_callback("Checking architecture metadata for model directory...")
                    # Auto-recovery for known repository directories or online fetch
                    known_repos = {
                        "compact_reasoning": "HuggingFaceTB/SmolLM2-135M-Instruct",
                        "embeddings_representation": "sentence-transformers/all-MiniLM-L6-v2",
                        "chat_instruct": "Qwen/Qwen2.5-0.5B-Instruct",
                        "code_generation": "Qwen/Qwen2.5-Coder-0.5B-Instruct"
                    }
                    matched_repo = None
                    for k, r in known_repos.items():
                        if k in model_dir.lower():
                            matched_repo = r
                            break

                    if matched_repo:
                        try:
                            import urllib.request
                            log_callback(f"Retrieving missing model architecture metadata for '{matched_repo}'...")
                            aux_files = ["config.json", "tokenizer.json", "tokenizer_config.json", "generation_config.json", "special_tokens_map.json"]
                            for af in aux_files:
                                dest = os.path.join(model_dir, af)
                                if not os.path.exists(dest):
                                    url = f"https://huggingface.co/{matched_repo}/raw/main/{af}"
                                    urllib.request.urlretrieve(url, dest)
                            if os.path.exists(config_path):
                                log_callback(f"Successfully configured '{matched_repo}' architecture metadata.")
                        except Exception as e_rec:
                            log_callback(f"Online metadata sync note: {e_rec}")

                    if not os.path.exists(config_path):
                        err_msg = (
                            f"Model configuration file ('config.json') is missing in '{model_dir}'. "
                            "Safetensors weight files require their companion architecture config to load. "
                            "Please ensure config.json is present in the folder, or select a self-contained .gguf model."
                        )
                        emit({"event": "loaded", "success": False, "error": err_msg})
                        return

                tok_candidates = [
                    os.path.join(model_dir, "tokenizer.json"),
                    os.path.join(model_dir, "tokenizer_config.json"),
                    os.path.join(model_dir, "vocab.json"),
                    os.path.join(model_dir, "vocab.txt")
                ]
                has_tokenizer = any(os.path.exists(f) for f in tok_candidates)
                
                self.tokenizer = None
                if not has_tokenizer:
                    log_callback("Note: No tokenizer config found in model directory. Trying standard fallback...")
                    for fallback_name in ["Qwen/Qwen2.5-0.5B", "gpt2"]:
                        try:
                            self.tokenizer = AutoTokenizer.from_pretrained(fallback_name, trust_remote_code=True)
                            log_callback(f"Attached fallback tokenizer ({fallback_name}).")
                            break
                        except Exception:
                            continue

                if self.tokenizer is None:
                    self.tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True, trust_remote_code=True)

                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token

                dev = "cuda:0" if (use_gpu and torch.cuda.is_available()) else "cpu"
                dtype = torch.float16 if dev != "cpu" else torch.float32

                self.model = AutoModelForCausalLM.from_pretrained(
                    model_dir,
                    device_map="auto" if dev != "cpu" else None,
                    torch_dtype=dtype,
                    local_files_only=True,
                    trust_remote_code=True
                )
                if dev == "cpu":
                    self.model = self.model.to("cpu")

                # Detect if the loaded model is an embedding/representation model
                self.is_embedding_model = False
                try:
                    cfg_dict = getattr(self.model, "config", None)
                    m_type = str(getattr(cfg_dict, "model_type", "")).lower()
                    archs = [str(a).lower() for a in getattr(cfg_dict, "architectures", [])]
                    if "bert" in m_type or any("bert" in a for a in archs) or "embeddings" in model_dir.lower():
                        self.is_embedding_model = True
                        log_callback("Notice: Model is a feature/embedding representation model (BERT architecture).")
                except Exception:
                    pass

                self.model_type = "transformers"
                self.device = dev
                emit({"event": "loaded", "success": True, "model_path": model_path, "device": self.device})
                log_callback(f"Model loaded successfully on {self.device}!")
            except Exception as e_final:
                self.model = None
                self.tokenizer = None
                self.model_path = None
                err_msg = str(e_final)
                if "Couldn't instantiate the backend tokenizer" in err_msg:
                    err_msg = "Model directory is missing tokenizer files (tokenizer.json). For single files without config, please select a .gguf model."
                elif "Should have a `model_type` key in its config.json" in err_msg or "Unrecognized model" in err_msg:
                    err_msg = f"Missing or invalid 'model_type' in '{model_dir}/config.json'. Please ensure valid config.json exists or select a .gguf model."
                emit({"event": "loaded", "success": False, "error": err_msg})


    def generate(self, prompt, max_new_tokens=64, temperature=0.7):
        if self.model is None:
            emit({"event": "error", "message": "No model loaded."})
            return

        if getattr(self, "is_embedding_model", False):
            model_name = os.path.basename(self.model_path or "model")
            notice = (
                f"ℹ️ Model Notice:\n\n"
                f"The active model '{model_name}' is a feature/embedding representation model (BERT architecture).\n"
                f"It is specialized for vector embeddings and semantic search rather than conversational text generation.\n\n"
                f"💡 For interactive conversation, code writing, and assistant responses, please select a Chat / Instruct model (such as Qwen 2.5 or SmolLM2) from the Models menu."
            )
            emit({"event": "token", "token": notice})
            emit({"event": "generation_complete", "text": notice})
            self._is_generating = False
            return

        self._is_generating = True
        self._cancel_requested = False

        start_time = time.time()
        generated_text = ""
        token_count = 0

        try:
            import torch

            # A. AirLLM layer streaming path
            if hasattr(self.model, "is_airllm") or self.model_type == "gguf_airllm":
                emit({"event": "status", "message": "Streaming layer-wise generation..."})
                tok = self.tokenizer or getattr(self.model, "tokenizer", None)
                if tok is None:
                    from transformers import AutoTokenizer
                    tok = AutoTokenizer.from_pretrained("gpt2")
                    tok.pad_token = tok.eos_token

                inputs = tok(prompt, return_tensors="pt")
                input_ids = inputs["input_ids"]

                max_tokens = min(int(max_new_tokens or 64), 64)
                curr_ids = input_ids
                for step in range(max_tokens):
                    if self._cancel_requested:
                        emit({"event": "status", "message": "Generation cancelled by user."})
                        break

                    with torch.no_grad():
                        out = self.model(curr_ids, use_cache=False)
                        next_logits = out.logits[:, -1, :]
                        if temperature > 0:
                            probs = torch.softmax(next_logits / max(temperature, 0.1), dim=-1)
                            next_token = torch.multinomial(probs, num_samples=1)
                        else:
                            next_token = torch.argmax(next_logits, dim=-1, keepdim=True)

                    token_id = next_token.item()
                    curr_ids = torch.cat([curr_ids, next_token], dim=1)
                    token_count += 1

                    piece = tok.decode([token_id], skip_special_tokens=True)
                    generated_text += piece
                    emit({"event": "token", "token": piece, "token_id": token_id})

                    if token_id == tok.eos_token_id:
                        break

            # B. Fast In-Memory Transformers / GGUF path
            else:
                tok = self.tokenizer
                inputs = tok(prompt, return_tensors="pt")
                if self.device != "cpu":
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}

                try:
                    from transformers import TextIteratorStreamer
                    streamer = TextIteratorStreamer(tok, skip_prompt=True, skip_special_tokens=True)
                    gen_kwargs = dict(
                        **inputs,
                        streamer=streamer,
                        max_new_tokens=max_new_tokens,
                        temperature=max(temperature, 0.01),
                        do_sample=(temperature > 0),
                        pad_token_id=tok.pad_token_id or tok.eos_token_id
                    )
                    gen_thread = threading.Thread(target=self.model.generate, kwargs=gen_kwargs)
                    gen_thread.start()

                    for new_text in streamer:
                        if self._cancel_requested:
                            break
                        generated_text += new_text
                        token_count += 1
                        emit({"event": "token", "token": new_text})
                    gen_thread.join(timeout=2.0)
                except Exception:
                    input_len = inputs["input_ids"].shape[1]
                    with torch.no_grad():
                        outputs = self.model.generate(
                            **inputs,
                            max_new_tokens=max_new_tokens,
                            temperature=max(temperature, 0.01),
                            do_sample=(temperature > 0),
                            pad_token_id=tok.pad_token_id or tok.eos_token_id
                        )
                    new_tokens = outputs[0][input_len:]
                    generated_text = tok.decode(new_tokens, skip_special_tokens=True)
                    token_count = len(new_tokens)
                    emit({"event": "token", "token": generated_text})

            elapsed = time.time() - start_time
            emit({
                "event": "generation_complete",
                "text": generated_text,
                "token_count": token_count,
                "elapsed_sec": round(elapsed, 2),
                "speed_tps": round(token_count / max(elapsed, 0.01), 2)
            })

        except Exception as e:
            emit({"event": "error", "message": f"Generation error: {e}"})
        finally:
            self._is_generating = False

    def cancel(self):
        self._cancel_requested = True
        emit({"event": "cancelled"})

def main():
    engine = UniversalAIEngine()
    emit({"event": "ready", "version": "2.0.0"})

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            action = req.get("action")

            if action == "compatibility_check":
                res = engine.check_compatibility(req.get("model_path"))
                emit({"event": "compatibility", "result": res})

            elif action == "load_model":
                threading.Thread(
                    target=engine.load_model,
                    args=(req.get("model_path"), req.get("use_gpu", True), req.get("compute_mode")),
                    daemon=True
                ).start()

            elif action == "generate":
                threading.Thread(
                    target=engine.generate,
                    args=(req.get("prompt", ""), req.get("max_new_tokens", 64), req.get("temperature", 0.7)),
                    daemon=True
                ).start()

            elif action == "cancel":
                engine.cancel()

            elif action == "ping":
                emit({"event": "pong"})

        except Exception as e:
            emit({"event": "error", "message": str(e)})

if __name__ == "__main__":
    main()
