import os
import json
import gc
import ctypes
import torch
import numpy as np
from transformers.modeling_gguf_pytorch_utils import (
    load_gguf_checkpoint, get_gguf_hf_weights_map,
    TENSOR_PROCESSORS, TensorProcessor,
)
from gguf import GGUFReader, GGMLQuantizationType
import gguf.quants
from transformers import AutoConfig, AutoModelForCausalLM

# ---------------------------------------------------------------------------
# madvise helper — tells the kernel to drop mmap pages from physical RAM.
# Without this, streaming 27 GB of GGUF data fills all 16 GB of RAM and OOMs.
# ---------------------------------------------------------------------------
try:
    _libc = ctypes.CDLL("libc.so.6", use_errno=True)
    _libc.madvise.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
    _libc.madvise.restype = ctypes.c_int
    _PAGE = os.sysconf("SC_PAGE_SIZE")
except Exception:
    _libc = None
    _PAGE = 4096

def _drop_pages(arr):
    """Best-effort: advise kernel that mmap pages backing *arr* are no longer needed."""
    if _libc is None:
        return
    try:
        a = np.asarray(arr)
        addr = a.ctypes.data
        nbytes = a.nbytes
        # align down / up to page boundaries
        start = addr & ~(_PAGE - 1)
        end = (addr + nbytes + _PAGE - 1) & ~(_PAGE - 1)
        _libc.madvise(ctypes.c_void_p(start), ctypes.c_size_t(end - start), ctypes.c_int(4))  # 4 = MADV_DONTNEED
    except Exception as e:
        import traceback
        traceback.print_exc()

# ---- GGUFTensor result type (same namedtuple transformers uses) ----
try:
    from transformers.modeling_gguf_pytorch_utils import GGUFTensor
except ImportError:
    from collections import namedtuple
    GGUFTensor = namedtuple("GGUFTensor", ["weights", "name", "metadata"])


# ---------------------------------------------------------------------------
# Qwen3.5 / Qwen3.6 GGUF (llama.cpp architecture tag: "qwen35")
# ---------------------------------------------------------------------------
# llama.cpp converts Qwen3.5/Qwen3.6 hybrid Transformer-SSM checkpoints into GGUF
# under the single architecture tag "qwen35".  Per-block tensor layout (from
# llama.cpp src/models/qwen35.cpp):
#
#   full-attention block : attn_norm, attn_q(gate fused, 2x width), attn_k, attn_v,
#                          attn_output, attn_q_norm, attn_k_norm, post_attention_norm,
#                          ffn_gate, ffn_up, ffn_down
#   linear (SSM) block   : attn_norm, attn_qkv(in_proj_qkv), attn_gate(in_proj_z),
#                          ssm_alpha(in_proj_a), ssm_beta(in_proj_b), ssm_conv1d,
#                          ssm_dt.bias(dt_bias), ssm_a(-exp(A_log)), ssm_norm, ssm_out,
#                          post_attention_norm, ffn_gate, ffn_up, ffn_down
#
# GGUF metadata keys are prefixed with the architecture tag, e.g. "qwen35.block_count",
# "qwen35.ssm.state_size", "qwen35.attention.recurrent_layers" ...
#
# The huggingface model_type for these weights is "qwen3_5_text" (Qwen3_5TextConfig).
# NOTE: transformers does NOT (yet) register "qwen35" in its GGUF config/tensor maps,
# so all qwen35 GGUF parsing + tensor mapping below is done by us.
_QWEN35_ARCHES = ("qwen35", "qwen35moe", "qwen3_5", "qwen3_5_text")


def _gguf_field_values(field):
    """Return the decoded value(s) of a single GGUF metadata field."""
    if field is None:
        return None
    try:
        parts = field.parts
        out = []
        for idx in field.data:
            part = parts[idx]
            if isinstance(part, bytes):
                out.append(part.decode("utf-8", errors="replace"))
            elif isinstance(part, np.ndarray):
                if part.dtype == np.uint8:
                    out.append(bytes(part).decode("utf-8", errors="replace"))
                else:
                    try:
                        out.append(part.item())
                    except ValueError:
                        out.append(part.tolist())
            else:
                out.append(float(part) if part.dtype.kind == "f" else int(part))
        return out[0] if len(out) == 1 else out
    except Exception:
        return None


def _gguf_read(reader, key, default=None):
    """Read one GGUF metadata field by exact key, returning decoded scalar / list."""
    return _gguf_field_values(reader.fields.get(key)) if key in reader.fields else default


def _gguf_arch(reader):
    """general.architecture of the GGUF file (e.g. 'qwen35', 'llama')."""
    return _gguf_read(reader, "general.architecture", "")


class Qwen35TensorProcessor(TensorProcessor):
    """Per-tensor transforms required to load qwen35 GGUF weights into the HF
    Qwen3.5-Text modules.  Everything else (incl. the attention q/k/v projections,
    where llama.cpp already stores gate-fused q in HF row order) is a plain copy;
    orientation is handled by dequantize_chunked() (ggml dims reversed)."""

    def __init__(self, config=None):
        super().__init__(config=config)

    def process(self, weights, name, **kwargs):
        if name.endswith(".ssm_conv1d.weight") and weights.ndim == 2:
            # GGUF: (channels, kernel) -> Conv1d weight (channels, 1, kernel)
            weights = np.expand_dims(weights, axis=1)
        elif name.endswith(".ssm_a"):
            # GGUF stores -exp(A_log)  ->  HF linear_attn.A_log = log(-a)
            weights = np.log(np.maximum(-weights.astype(np.float32), 1e-8)).astype(weights.dtype)
        return GGUFTensor(weights, name, {})


def _build_qwen35_hf_config(reader, arch):
    """Convert qwen35 GGUF metadata into a Qwen3_5TextConfig-compatible dict.

    Keys may be present either with the llama.cpp prefix ("qwen35.block_count") or
    bare ("block_count"), depending on how the file was written.
    """
    def read(suffix, default=None):
        v = _gguf_read(reader, f"{arch}.{suffix}")
        if v is None:
            v = _gguf_read(reader, suffix)
        return default if v is None else v

    num_layers = int(read("block_count"))
    hidden_size = int(read("embedding_length"))
    num_heads = int(read("attention.head_count"))

    head_dim = read("attention.key_length")
    if head_dim is None:
        head_dim = int(read("embedding_length") // num_heads)
    head_dim = int(head_dim)

    # Which layers are linear (SSM) vs full attention?  llama.cpp stores either an
    # explicit per-layer array or a full-attention interval (default every 4th layer
    # is full attention, i.e. layer_types[(i+1) % 4 == 0] == "full_attention").
    recurrent = read("attention.recurrent_layers")
    layer_types = []
    if isinstance(recurrent, list) and len(recurrent) >= num_layers:
        layer_types = [
            "linear_attention" if bool(recurrent[i]) else "full_attention"
            for i in range(num_layers)
        ]
    else:
        interval = int(read("full_attention_interval", 4) or 4)
        interval = max(1, interval)
        layer_types = [
            "linear_attention" if bool((i + 1) % interval) else "full_attention"
            for i in range(num_layers)
        ]

    # SSM dimensions (Gated DeltaNet)
    ssm_state = int(read("ssm.state_size", 128) or 128)
    ssm_conv = int(read("ssm.conv_kernel", 4) or 4)
    ssm_group = int(read("ssm.group_count", 16) or 16)          # linear_num_key_heads
    ssm_dt_rank = int(read("ssm.time_step_rank", 32) or 32)     # linear_num_value_heads

    rope_theta = read("rope.freq_base")
    rope_dim = read("rope.dimension_count")
    partial_rot = (float(rope_dim) / float(head_dim)) if rope_dim else 0.25
    rope_parameters = {
        "rope_type": "default",
        "rope_theta": float(rope_theta) if rope_theta else 1000000.0,
        "partial_rotary_factor": float(partial_rot) if 0.0 < float(partial_rot) <= 1.0 else 0.25,
    }

    has_output = any(t.name == "output.weight" for t in reader.tensors)

    config = {
        "architectures": ["Qwen3_5TextForCausalLM"],
        "hidden_size": hidden_size,
        "intermediate_size": int(read("feed_forward_length")),
        "num_hidden_layers": num_layers,
        "num_attention_heads": num_heads,
        "num_key_value_heads": int(read("attention.head_count_kv", num_heads) or num_heads),
        "max_position_embeddings": int(read("context_length", 32768) or 32768),
        "hidden_act": "silu",
        "rms_norm_eps": float(read("attention.layer_norm_rms_epsilon", 1e-6) or 1e-6),
        "head_dim": head_dim,
        "rope_parameters": rope_parameters,
        "linear_num_key_heads": ssm_group,
        "linear_num_value_heads": ssm_dt_rank,
        "linear_key_head_dim": ssm_state,
        "linear_value_head_dim": ssm_state,
        "linear_conv_kernel_dim": ssm_conv,
        "layer_types": layer_types,
        "tie_word_embeddings": not has_output,
        "bos_token_id": read("bos_token_id"),
        "eos_token_id": read("eos_token_id"),
    }
    return config


def _build_qwen35_hf_to_gguf_map(num_layers, layer_types):
    """Build {hf_param_name: gguf_tensor_name} for a qwen35 GGUF.

    Full-attention blocks store their fused gate inside ``attn_q`` (llama.cpp's
    create_tensor_qkv with n_embd_head_k*n_head*2), which is exactly the layout
    Qwen3_5Text self_attn.q_proj expects (query rows interleaved with gate rows per
    head), so a plain copy is correct.  Linear (SSM) blocks store the delta-net input
    projections as attn_qkv / attn_gate / ssm_alpha / ssm_beta -> in_proj_qkv /
    in_proj_z / in_proj_a / in_proj_b.
    """
    hf_to_gguf = {}
    common = {
        "attn_norm.weight": ".input_layernorm.weight",
        "post_attention_norm.weight": ".post_attention_layernorm.weight",
        "ffn_gate.weight": ".mlp.gate_proj.weight",
        "ffn_up.weight": ".mlp.up_proj.weight",
        "ffn_down.weight": ".mlp.down_proj.weight",
    }
    for i, layer_type in enumerate(layer_types):
        prefix = f"model.layers.{i}"
        if layer_type == "linear_attention":
            lin = {
                "attn_qkv.weight": prefix + ".linear_attn.in_proj_qkv.weight",
                "attn_gate.weight": prefix + ".linear_attn.in_proj_z.weight",
                "ssm_alpha.weight": prefix + ".linear_attn.in_proj_a.weight",
                "ssm_beta.weight": prefix + ".linear_attn.in_proj_b.weight",
                "ssm_conv1d.weight": prefix + ".linear_attn.conv1d.weight",
                "ssm_dt.bias": prefix + ".linear_attn.dt_bias",
                "ssm_a": prefix + ".linear_attn.A_log",
                "ssm_norm.weight": prefix + ".linear_attn.norm.weight",
                "ssm_out.weight": prefix + ".linear_attn.out_proj.weight",
            }
        else:
            lin = {
                "attn_q.weight": prefix + ".self_attn.q_proj.weight",
                "attn_k.weight": prefix + ".self_attn.k_proj.weight",
                "attn_v.weight": prefix + ".self_attn.v_proj.weight",
                "attn_output.weight": prefix + ".self_attn.o_proj.weight",
                "attn_q_norm.weight": prefix + ".self_attn.q_norm.weight",
                "attn_k_norm.weight": prefix + ".self_attn.k_norm.weight",
            }
        for gguf_suffix, hf_suffix in common.items():
            lin[gguf_suffix] = prefix + hf_suffix
        for gguf_tail, hf_name in lin.items():
            hf_to_gguf[hf_name] = f"blk.{i}.{gguf_tail}"

    hf_to_gguf["model.embed_tokens.weight"] = "token_embd.weight"
    hf_to_gguf["model.norm.weight"] = "output_norm.weight"
    hf_to_gguf["lm_head.weight"] = "output.weight"
    return hf_to_gguf


# ---------------------------------------------------------------------------
# Memory-efficient chunked dequantizer
# ---------------------------------------------------------------------------
def dequantize_chunked(tensor):
    """Dequantize a GGUF tensor in small chunks so peak RAM stays low."""
    qtype  = tensor.tensor_type
    n_elem = int(tensor.n_elements)
    shape  = tuple(int(x) for x in reversed(tensor.shape))

    out = torch.empty(n_elem, dtype=torch.float16)

    if qtype in (GGMLQuantizationType.F32, GGMLQuantizationType.F16):
        # tensor.data may be raw uint8 bytes OR an already-typed memmap
        raw = np.asarray(tensor.data)
        flat = raw.reshape(-1)                   # flatten without copy

        if qtype == GGMLQuantizationType.F32:
            if flat.dtype == np.uint8:
                flat = flat.view(np.float32)
            elif flat.dtype != np.float32:
                flat = flat.astype(np.float32)
        else:  # F16
            if flat.dtype == np.uint8:
                flat = flat.view(np.float16)
            elif flat.dtype != np.float16:
                flat = flat.astype(np.float16)

        # flat is now 1-D in the correct dtype — chunk by element count
        chunk = 1024 * 1024
        for i in range(0, n_elem, chunk):
            end = min(i + chunk, n_elem)
            out[i:end] = torch.from_numpy(flat[i:end].copy()).to(torch.float16)
        return out.view(shape)

    # ---- quantized path (Q4_0, Q8_0, etc.) ----
    trait = gguf.quants._type_traits.get(qtype)
    if not trait:
        raise NotImplementedError(f"GGUF quant type {qtype} unsupported in AirLLM wrapper.")

    raw = np.asarray(tensor.data)
    if raw.dtype != np.uint8:
        raw = raw.view(np.uint8)
    raw = raw.reshape(-1)

    chunk_blocks = 10000
    chunk_bytes  = chunk_blocks * trait.type_size
    n_bytes      = len(raw)
    idx = 0
    for boff in range(0, n_bytes, chunk_bytes):
        bend = min(boff + chunk_bytes, n_bytes)
        fp32 = trait.dequantize(raw[boff:bend])
        elems = fp32.size
        out[idx : idx + elems] = torch.from_numpy(fp32).view(-1).to(torch.float16)
        idx += elems
    return out.view(shape)


# ---------------------------------------------------------------------------
# GGUFPersister — AirLLM calls this to load one layer at a time
# ---------------------------------------------------------------------------
class GGUFPersister:
    def __init__(self, reader, hf_to_gguf, processor, parsed, tensor_key_mapping):
        self.reader = reader
        self.hf_to_gguf = hf_to_gguf
        self.processor = processor
        self.parsed = parsed
        self.tensor_key_mapping = tensor_key_mapping
        self.tensor_map = {t.name: i for i, t in enumerate(reader.tensors)}

    def model_persist_exist(self, layer_name, saving_path):
        return True

    def persist_model(self, state_dict, layer_name, saving_path):
        pass

    def load_model(self, layer_name, path):
        state_dict = {}
        for hf_name, gguf_name in self.hf_to_gguf.items():
            if not (hf_name == layer_name or hf_name.startswith(layer_name + ".")):
                continue
            tensor_idx = self.tensor_map.get(gguf_name)
            if tensor_idx is None:
                continue

            tensor = self.reader.tensors[tensor_idx]
            pt = dequantize_chunked(tensor)

            # Run through processor for SSM-specific transforms
            np_w = pt.numpy()                    # view (no copy) of the float16 tensor
            res = self.processor.process(
                weights=np_w,
                name=gguf_name,
                tensor_key_mapping=self.tensor_key_mapping,
                parsed_parameters=self.parsed,
            )

            if res.weights is np_w:
                # Processor did not modify anything — reuse the torch tensor directly
                state_dict[hf_name] = pt
            else:
                # Direct PyTorch tensor from numpy
                state_dict[hf_name] = torch.from_numpy(np.ascontiguousarray(res.weights))
                del pt                           # free the original

            del np_w, res                        # free intermediates immediately
            _drop_pages(tensor.data)             # drop mmap pages to avoid OOM

        gc.collect()
        return state_dict


# ---------------------------------------------------------------------------
# Tokenizer builder (unchanged from earlier)
# ---------------------------------------------------------------------------
def _build_tokenizer_from_gguf(reader, dummy_dir, config):
    """Extract tokenizer vocabulary from GGUF metadata and save as HF tokenizer files."""
    import json as _json
    fields = reader.fields

    # Extract token list
    tokens = []
    if 'tokenizer.ggml.tokens' in fields:
        token_field = fields['tokenizer.ggml.tokens']
        for part_idx in token_field.data:
            tokens.append(str(bytes(token_field.parts[part_idx]), encoding='utf-8', errors='replace'))

    if not tokens:
        return None

    # Extract scores
    scores = []
    if 'tokenizer.ggml.scores' in fields:
        score_field = fields['tokenizer.ggml.scores']
        for part_idx in score_field.data:
            part = score_field.parts[part_idx]
            val = float(part.item() if hasattr(part, "item") else part)
            scores.append(val)

    # Extract token types
    token_types = []
    if 'tokenizer.ggml.token_type' in fields:
        tt_field = fields['tokenizer.ggml.token_type']
        for part_idx in tt_field.data:
            part = tt_field.parts[part_idx]
            token_types.append(int(part.item() if hasattr(part, "item") else part))

    # Get model type
    tok_model = "gpt2"
    if 'tokenizer.ggml.model' in fields:
        tm_field = fields['tokenizer.ggml.model']
        tok_model = str(bytes(tm_field.parts[tm_field.data[0]]), encoding='utf-8', errors='replace')

    # Get special tokens
    bos_id = None
    eos_id = None
    if 'tokenizer.ggml.bos_token_id' in fields:
        f = fields['tokenizer.ggml.bos_token_id']
        part = f.parts[f.data[0]]
        bos_id = int(part.item() if hasattr(part, "item") else part)
    if 'tokenizer.ggml.eos_token_id' in fields:
        f = fields['tokenizer.ggml.eos_token_id']
        part = f.parts[f.data[0]]
        eos_id = int(part.item() if hasattr(part, "item") else part)

    # Build a simple vocab dict for a PreTrainedTokenizerFast
    vocab = {tok: i for i, tok in enumerate(tokens)}

    # Build merges if BPE
    merges = []
    if 'tokenizer.ggml.merges' in fields:
        merge_field = fields['tokenizer.ggml.merges']
        for part_idx in merge_field.data:
            merges.append(str(bytes(merge_field.parts[part_idx]), encoding='utf-8', errors='replace'))

    # Write tokenizer files
    bos_token = tokens[bos_id] if bos_id is not None and bos_id < len(tokens) else "<|endoftext|>"
    eos_token = tokens[eos_id] if eos_id is not None and eos_id < len(tokens) else "<|endoftext|>"

    # Build tokenizer.json for tokenizers library
    added_tokens = []
    special_ids = set()
    if bos_id is not None:
        special_ids.add(bos_id)
    if eos_id is not None:
        special_ids.add(eos_id)
    # Mark control/special tokens
    for i, tok in enumerate(tokens):
        if i < len(token_types) and token_types[i] in (3, 4):  # CONTROL or USER_DEFINED special
            special_ids.add(i)

    for tid in sorted(special_ids):
        if tid < len(tokens):
            added_tokens.append({
                "id": tid,
                "content": tokens[tid],
                "single_word": False,
                "lstrip": False,
                "rstrip": False,
                "normalized": False,
                "special": True
            })

    tokenizer_json = {
        "version": "1.0",
        "added_tokens": added_tokens,
        "model": {
            "type": "BPE",
            "vocab": vocab,
            "merges": merges
        },
        "pre_tokenizer": {"type": "ByteLevel", "add_prefix_space": False, "trim_offsets": True, "use_regex": True},
        "post_processor": {
            "type": "ByteLevel",
            "add_prefix_space": True,
            "trim_offsets": False,
            "use_regex": True
        },
        "decoder": {"type": "ByteLevel", "add_prefix_space": True, "trim_offsets": True, "use_regex": True},
        "normalizer": None,
    }

    with open(os.path.join(dummy_dir, "tokenizer.json"), "w") as f:
        _json.dump(tokenizer_json, f)

    tokenizer_config = {
        "tokenizer_class": "PreTrainedTokenizerFast",
        "bos_token": bos_token,
        "eos_token": eos_token,
        "model_max_length": config.get("max_position_embeddings", 32768),
    }
    with open(os.path.join(dummy_dir, "tokenizer_config.json"), "w") as f:
        _json.dump(tokenizer_config, f)

    # Now load it
    from transformers import PreTrainedTokenizerFast
    try:
        tok = PreTrainedTokenizerFast(tokenizer_file=os.path.join(dummy_dir, "tokenizer.json"))
        if bos_id is not None and bos_id < len(tokens):
            tok.bos_token = bos_token
        if eos_id is not None and eos_id < len(tokens):
            tok.eos_token = eos_token
            tok.pad_token = eos_token
        return tok
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Qwen3.5 / Qwen3.6 hybrid loader (architecture "qwen35")
# ---------------------------------------------------------------------------
def _load_qwen35_via_airllm(gguf_path, callback=None):
    """Layer-wise streaming load for qwen35 (Qwen3.5/Qwen3.6 hybrid SSM) GGUFs.

    The HF side needs Qwen3_5TextConfig/Qwen3_5TextForCausalLM (transformers >= 5.2),
    and AirLLM needs its generic hook-based ``AirLLMBaseModel`` (which lets
    transformers drive the forward pass, so the Gated-DeltaNet / SSM layers actually
    run correctly).  The GGUF metadata + tensor mapping is handled entirely here,
    because transformers does not (yet) ship a qwen35 GGUF reader.
    """
    from airllm.persist import model_persister as am_persister
    import airllm.utils
    import airllm.airllm_base
    from airllm import AutoModel

    if callback:
        callback("Qwen3.5 wrapper: reading GGUF metadata (qwen35 architecture)...")

    reader = GGUFReader(gguf_path)
    arch = _gguf_arch(reader) or "qwen35"
    config = _build_qwen35_hf_config(reader, arch)
    config["model_type"] = "qwen3_5_text"

    # ---- sanity checks with actionable upgrade hints ----
    try:
        from transformers import Qwen3_5TextConfig  # noqa: F401  (verify support)
    except Exception as e:
        raise RuntimeError(
            "Qwen3.5 (qwen35 GGUF) requires a transformers release that ships "
            "Qwen3_5TextConfig (transformers >= 5.2). This environment's transformers "
            f"does not support it ({e}). Run:  pip install -U 'transformers>=5.2'"
        ) from e

    airllm_has_generic_base = (
        hasattr(airllm.airllm_base, "AirLLMBaseModel")
        and hasattr(airllm.airllm_base.AirLLMBaseModel, "_install_streaming_hooks")
        and hasattr(airllm.utils, "load_layer")
    )
    if not airllm_has_generic_base:
        raise RuntimeError(
            "Qwen3.5 (qwen35 GGUF) layers are hybrid SSM layers and can only be streamed "
            "by AirLLM's generic AirLLMBaseModel (transformers-driven forward pass). The "
            "installed AirLLM is too old for that. Run:  pip install -U airllm"
        )

    # ---- dummy model dir (config.json + tokenizer for AutoConfig/AutoTokenizer) ----
    dummy_dir = os.path.join(os.path.dirname(gguf_path), ".airllm_gguf_cache")
    os.makedirs(dummy_dir, exist_ok=True)
    with open(os.path.join(dummy_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    with open(os.path.join(dummy_dir, "generation_config.json"), "w", encoding="utf-8") as f:
        json.dump({"max_new_tokens": 4096}, f, indent=2)

    if callback:
        callback("Qwen3.5 wrapper: extracting tokenizer from GGUF metadata...")
    tok = _build_tokenizer_from_gguf(reader, dummy_dir, config)

    # ---- tensor map (gguf -> hf) ----
    layer_types = config.get("layer_types") or []
    hf_to_gguf_map = _build_qwen35_hf_to_gguf_map(len(layer_types), layer_types)
    tensor_key_mapping = {v: k for k, v in hf_to_gguf_map.items()}  # gguf -> hf

    processor = Qwen35TensorProcessor(config=config)
    persister = GGUFPersister(reader, hf_to_gguf_map, processor, {"config": config}, tensor_key_mapping)

    # ---- monkey-patch AirLLM so it streams straight out of the GGUF ----
    def _mock_find(*a, **k):
        return (dummy_dir, dummy_dir)

    airllm.utils.find_or_create_local_splitted_path = _mock_find
    airllm.airllm_base.find_or_create_local_splitted_path = _mock_find
    am_persister.ModelPersister.get_model_persister = classmethod(lambda cls: persister)

    # New hook-based AirLLMBaseModel reads per-layer shards through utils.load_layer
    # (checkpoint_path, layer_name). Serve those calls from the GGUF persister.
    def _mock_load_layer(checkpoint_path, layer_name, *a, **k):
        return persister.load_model(layer_name, checkpoint_path)

    airllm.utils.load_layer = _mock_load_layer
    airllm.airllm_base.load_layer = _mock_load_layer
    if hasattr(airllm.utils, "load_layer_subset"):
        airllm.utils.load_layer_subset = lambda path, name, keys, *a, **k: persister.load_model(name, path)
        airllm.airllm_base.load_layer_subset = airllm.utils.load_layer_subset
    if hasattr(airllm.utils, "layer_tensor_names"):
        airllm.utils.layer_tensor_names = lambda path, name, *a, **k: list(
            persister.hf_to_gguf
        )
        airllm.airllm_base.layer_tensor_names = airllm.utils.layer_tensor_names

    if callback:
        callback("Qwen3.5 wrapper: initializing AirLLM streaming model (meta skeleton, layer-by-layer)...")
    gc.collect()
    dev = 'cuda:0' if torch.cuda.is_available() else 'cpu'
    model = AutoModel.from_pretrained(dummy_dir, device=dev)
    try:
        setattr(model, 'is_airllm', True)
    except Exception:
        pass

    # ---- safety-net: keep Conv1d module hyper-params in sync after shape adoption ----
    _orig_adopt = model._adopt_checkpoint_shape

    def _patched_adopt(param_name, value, _orig=_orig_adopt):
        _orig(param_name, value)
        if "conv1d.weight" in param_name and getattr(value, "ndim", 0) == 3:
            module_path = param_name.rsplit('.', 1)[0]
            try:
                conv_module = model.model.get_submodule(module_path)
            except (AttributeError, ValueError):
                return
            if isinstance(conv_module, torch.nn.Conv1d):
                new_out = value.shape[0]
                if conv_module.groups != new_out:
                    conv_module.groups = new_out
                    conv_module.in_channels = new_out
                    conv_module.out_channels = new_out

    try:
        model._adopt_checkpoint_shape = _patched_adopt
    except Exception:
        pass

    # ---- tokenizer ----
    if tok is not None:
        model.tokenizer = tok
    else:
        try:
            from transformers import AutoTokenizer
            tok = AutoTokenizer.from_pretrained(
                os.path.dirname(gguf_path),
                gguf_file=os.path.basename(gguf_path),
                local_files_only=True,
            )
            model.tokenizer = tok
        except Exception:
            if callback:
                callback("Warning: could not extract a tokenizer from this GGUF.")

    if callback:
        callback("Qwen3.5 GGUF loaded via AirLLM layer streaming -> Ready.")
    return model


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def load_gguf_via_airllm(gguf_path, callback=None):
    from airllm.persist import model_persister as am_persister
    import airllm.utils
    import airllm.airllm_base
    from airllm import AutoModel

    if callback:
        callback("AirLLM GGUF Wrapper: Reading GGUF config (low memory mode)...")

    # ---- lightweight probe first: llama.cpp tags Qwen3.5/Qwen3.6 as "qwen35",
    # and transformers does not know that architecture in its GGUF reader. ----
    _probe = GGUFReader(gguf_path)
    _probe_arch = _gguf_arch(_probe)
    if isinstance(_probe_arch, list) and len(_probe_arch) > 0:
        _probe_arch = _probe_arch[0]
    if _probe_arch in _QWEN35_ARCHES:
        del _probe
        gc.collect()
        return _load_qwen35_via_airllm(gguf_path, callback=callback)
    del _probe
    gc.collect()

    parsed = load_gguf_checkpoint(gguf_path, return_tensors=False)
    config = parsed["config"]
    
    arch = config.get("architecture", config.get("model_type", "llama"))
    model_type = config.get("model_type", "llama")

    if isinstance(arch, list) and len(arch) > 0:
        arch = arch[0]
    if isinstance(model_type, list) and len(model_type) > 0:
        model_type = model_type[0]

    # Safety net for any GGUF whose metadata lands on a qwen35-ish model_type but
    # whose architecture tag was not caught above.
    if arch in _QWEN35_ARCHES or model_type in _QWEN35_ARCHES:
        del parsed
        gc.collect()
        return _load_qwen35_via_airllm(gguf_path, callback=callback)

    ProcessorClass = TENSOR_PROCESSORS.get(arch, TensorProcessor)
    
    dummy_dir = os.path.join(os.path.dirname(gguf_path), ".airllm_gguf_cache")
    os.makedirs(dummy_dir, exist_ok=True)
    with open(os.path.join(dummy_dir, "config.json"), "w") as f:
        json.dump(config, f, indent=2)
    with open(os.path.join(dummy_dir, "generation_config.json"), "w") as f:
        json.dump({"max_new_tokens": 128}, f, indent=2)

    processor = ProcessorClass(config=config)

    # ---- build HF config & model skeleton (temporary, just for name mapping) ----
    config_kwargs = config.copy()
    config_kwargs.pop("model_type", None)
    hf_config = AutoConfig.for_model(config["model_type"], **config_kwargs)
    model_class = AutoModelForCausalLM._model_mapping[type(hf_config)]

    with torch.device("meta"):
        model_to_load = model_class(hf_config)
    tensor_key_mapping = get_gguf_hf_weights_map(model_to_load, processor)
    del model_to_load, hf_config, model_class  # free ~2GB skeleton
    gc.collect()

    # ---- open GGUF and build the GGUF→HF name map ----
    if callback:
        callback("AirLLM GGUF Wrapper: Indexing tensors (no memory mapping copy)...")
    reader = GGUFReader(gguf_path)

    hf_to_gguf_map = {}
    for tensor in reader.tensors:
        name = tensor.name
        dummy_weights = np.zeros(1)
        try:
            res = processor.process(
                dummy_weights, name,
                tensor_key_mapping=tensor_key_mapping,
                parsed_parameters=parsed,
            )
            if res.name and res.name in tensor_key_mapping:
                hf_to_gguf_map[tensor_key_mapping[res.name]] = tensor.name
        except Exception:
            pass

    # ---- Fix: manually map dt_bias (unmapped because HF names it "dt_bias" ----
    # ---- while the GGUF name mapper only knows "dt_proj")                   ----
    for tensor in reader.tensors:
        if tensor.name.endswith(".ssm_dt.bias"):
            blk_num = tensor.name.split(".")[1]
            hf_name = f"model.layers.{blk_num}.linear_attn.dt_bias"
            hf_to_gguf_map[hf_name] = tensor.name

    # ---- build tokenizer ----
    if callback:
        callback("AirLLM GGUF Wrapper: Extracting tokenizer from GGUF metadata...")
    tok = _build_tokenizer_from_gguf(reader, dummy_dir, config)

    # ---- free parsed dict (persister only needs tensor_key_mapping) ----
    # Keep a minimal copy for the processor's parsed_parameters argument
    parsed_minimal = {"config": config}
    del parsed
    gc.collect()

    # ---- monkey-patch AirLLM ----
    _orig_find = airllm.utils.find_or_create_local_splitted_path

    def _mock_find(*a, **k):
        return (dummy_dir, dummy_dir)

    airllm.utils.find_or_create_local_splitted_path = _mock_find
    airllm.airllm_base.find_or_create_local_splitted_path = _mock_find

    persister = GGUFPersister(reader, hf_to_gguf_map, processor, parsed_minimal, tensor_key_mapping)

    # We must patch get_model_persister because AirLLM calls it everywhere
    am_persister.ModelPersister.get_model_persister = classmethod(lambda cls: persister)

    if callback:
        callback("AirLLM GGUF Wrapper: Initializing AirLLM Base Model...")
    gc.collect()  # free everything before AirLLM allocates its own skeleton
    dev = 'cuda:0' if torch.cuda.is_available() else 'cpu'
    model = AutoModel.from_pretrained(dummy_dir, device=dev)

    # Safety-net: monkey-patch _adopt_checkpoint_shape so that when a Conv1d
    # weight is resized, the module's .groups / .in_channels / .out_channels
    # are updated too.  Without this, F.conv1d crashes with
    #   "expected weight to be divisible by groups at dimension 0".
    _orig_adopt = model._adopt_checkpoint_shape

    def _patched_adopt(param_name, value, _orig=_orig_adopt):
        _orig(param_name, value)
        # If this is a conv weight that changed dim-0, fix up the Conv module.
        if "conv1d.weight" in param_name and value.ndim == 3:
            module_path = param_name.rsplit('.', 1)[0]  # e.g. "model.layers.0.linear_attn.conv1d"
            try:
                conv_module = model.model.get_submodule(module_path)
            except (AttributeError, ValueError):
                return
            if isinstance(conv_module, torch.nn.Conv1d):
                new_out = value.shape[0]
                if conv_module.groups != new_out:
                    conv_module.groups = new_out
                    conv_module.in_channels = new_out
                    conv_module.out_channels = new_out

    model._adopt_checkpoint_shape = _patched_adopt

    # Attach tokenizer
    if tok is not None:
        model.tokenizer = tok
    else:
        # Last resort: try AutoTokenizer with gguf_file (may fail for some archs)
        try:
            from transformers import AutoTokenizer
            tok = AutoTokenizer.from_pretrained(
                os.path.dirname(gguf_path),
                gguf_file=os.path.basename(gguf_path),
                local_files_only=True,
            )
            model.tokenizer = tok
        except Exception:
            if callback:
                callback("Warning: Could not extract tokenizer from GGUF. Generation may use fallback tokenizer.")

    return model
