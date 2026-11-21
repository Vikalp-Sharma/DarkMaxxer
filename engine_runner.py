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
            is_gguf = lower.endswith(".gguf") or os.path.isfile(model_path)

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

                self.model_type = "transformers"
                self.device = dev
                emit({"event": "loaded", "success": True, "model_path": model_path, "device": self.device})
            except Exception as e_final:
                self.model = None
                self.tokenizer = None
                self.model_path = None
                emit({"event": "loaded", "success": False, "error": str(e_final)})

    def generate(self, prompt, max_new_tokens=64, temperature=0.7):
        if self.model is None:
            emit({"event": "error", "message": "No model loaded."})
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
