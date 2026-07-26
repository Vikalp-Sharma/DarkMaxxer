<div align="center">

<img src="gui/logo.png" alt="DarkMaxxer Logo" width="160" />

# DarkMaxxer

### The Ultimate Local AI Coding IDE for Windows

*Run 70B+ parameter language models on consumer hardware. No cloud. No API keys. No compromises.*

<br />

[![Version](https://img.shields.io/badge/v3.0.0-purple?style=for-the-badge&label=Release&labelColor=1a1a2e&color=6C63FF)](https://github.com/Vikalp-Sharma/DarkMaxxer/releases)
[![Windows](https://img.shields.io/badge/Windows_10_%2F_11-0078D6?style=for-the-badge&logo=windows11&logoColor=white&labelColor=1a1a2e)](https://github.com/Vikalp-Sharma/DarkMaxxer)
[![Python](https://img.shields.io/badge/Python_3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white&labelColor=1a1a2e)](https://python.org)
[![License](https://img.shields.io/badge/Proprietary-E10098?style=for-the-badge&logo=gnu-privacy-guard&logoColor=white&labelColor=1a1a2e)](LICENSE)

[![AirLLM](https://img.shields.io/badge/Engine-AirLLM-FF6F00?style=flat-square&logo=pytorch&logoColor=white)](https://github.com/lyogavin/airllm)
[![GGUF](https://img.shields.io/badge/Format-GGUF-00C7B7?style=flat-square&logo=llvm&logoColor=white)](https://github.com/ggerganov/ggml)
[![HuggingFace](https://img.shields.io/badge/Models-HuggingFace-FFD21E?style=flat-square&logo=huggingface&logoColor=black)](https://huggingface.co)
[![PyWebView](https://img.shields.io/badge/GUI-PyWebView-4FC08D?style=flat-square&logo=googlechrome&logoColor=white)](https://pywebview.flowrl.com)
[![MCP](https://img.shields.io/badge/Protocol-MCP-8B5CF6?style=flat-square&logo=lightning&logoColor=white)](https://modelcontextprotocol.io)

<br />

[![Offline](https://img.shields.io/badge/🔒_100%25_Offline-No_Telemetry-10B981?style=flat-square)](https://github.com/Vikalp-Sharma/DarkMaxxer)
[![Signed](https://img.shields.io/badge/🔏_Code_Signed-SMXF_Certificate-6366F1?style=flat-square)](https://github.com/Vikalp-Sharma/DarkMaxxer)
[![GPU](https://img.shields.io/badge/⚡_Layer--Wise-GPU_Offloading-F59E0B?style=flat-square)](https://github.com/Vikalp-Sharma/DarkMaxxer)
[![Agentic](https://img.shields.io/badge/🤖_Agentic-File_System_Tools-EC4899?style=flat-square)](https://github.com/Vikalp-Sharma/DarkMaxxer)

---

**[Features](#-features)** · **[Quick Start](#-quick-start)** · **[Architecture](#-architecture)** · **[Models](#-supported-models)** · **[MCP Tools](#-autonomous-tool-protocols)** · **[FAQ](#-faq)**

</div>

<br />

## 🌌 What is DarkMaxxer?

**DarkMaxxer** is a fully air-gapped, local-first AI coding IDE for Windows that puts enterprise-class large language models directly on your desktop — with zero cloud dependencies, zero API keys, and zero telemetry.

While cloud IDEs like Cursor, Copilot, and Windsurf pipe your proprietary code through remote servers, DarkMaxxer keeps **everything on your hardware**. Using AirLLM's revolutionary layer-wise GPU offloading, it runs 70B+ parameter models on consumer GPUs that would traditionally require 140GB+ of VRAM.

> **💡 Think of it as:** A private, offline Cursor that runs Llama 3 70B on your gaming PC.

<br />

## ✨ Features

<table>
<tr>
<td width="50%">

### ⚡ Layer-Wise GPU Offloading
Run 70B+ models on 8-16GB VRAM GPUs. AirLLM dynamically loads individual neural network layers between GPU, RAM, and disk during inference — no model sharding or quantization compromises needed.

### 🔒 100% Air-Gapped & Private  
Zero cloud calls. Zero API keys. Zero telemetry. Your code, conversations, and proprietary algorithms never leave your machine. Period.

### 🤖 Autonomous Agentic Workspace
The AI doesn't just chat — it **codes**. Structured tool calls (`CREATE_FILE`, `EDIT_FILE`, `DELETE_FILE`, `READ_FILE`, `RENAME_FILE`, `APPEND_FILE`) interact with your live workspace in real-time.

</td>
<td width="50%">

### 🔌 External MCP Integration
Connect external Model Context Protocol servers (GitHub, databases, APIs) directly from Settings. The AI discovers available tools and calls them autonomously via JSON-RPC over stdio.

### 🎨 Glassmorphic Nebula UI
Built with Chromium-backed `pywebview` and a custom design system featuring dynamic starfields, glowing nebula gradients, glassmorphism cards, and responsive micro-animations.

### 🧠 Persistent Everything
Folder state, chat history, terminal logs, sidebar position, active model — everything persists across sessions. Close the app, reopen it, and pick up exactly where you left off.

</td>
</tr>
</table>

<details>
<summary><b>📋 Full Feature List</b></summary>

| Category | Feature | Description |
|:---|:---|:---|
| 🧠 **AI Engine** | Layer-Wise Offloading | 70B models on consumer GPUs via AirLLM |
| | GGUF Support | Native quantized model loading with embedded tokenizers |
| | HuggingFace Transformers | Direct `.safetensors`, `.bin`, `.pth` loading |
| | Real-Time Interruption | Pause/cancel generation mid-token with ⏸ button |
| | Streaming Output | Token-by-token response rendering |
| 🔧 **Agentic Tools** | File Operations | CREATE, EDIT, READ, DELETE, RENAME, APPEND |
| | External MCP | Connect any MCP-compatible server via stdio |
| | Sandboxed Workspace | All file ops scoped to active project directory |
| | Smart Feedback | Clean tool result badges (✅ Created, 📝 Renamed, etc.) |
| 🎨 **Interface** | Nebula Theme | Dark glassmorphic UI with animated starfield |
| | File Explorer | Expandable/collapsible folder tree with file editor |
| | Split Terminal | Inline + pop-out terminal with real-time streaming |
| | Code Highlighting | Syntax-aware code blocks with one-click copy |
| | Responsive Layout | Fluid sidebar, chat, and settings panels |
| 💾 **Persistence** | Chat Memory | Conversation history with multi-thread support |
| | Workspace State | Auto-restore explorer tab, folder, and scroll position |
| | Config Manager | JSON-based settings with hot-reload |
| | Terminal Logs | Persistent across tab switches |
| 🔒 **Security** | Air-Gapped | Zero network calls during operation |
| | Code-Signed | SMXF certificate with LocalMachine trust |
| | MOTW Removal | Installer strips Zone.Identifier from all files |
| | Defender Exclusion | Auto-whitelists install directory |
| 📦 **Distribution** | Single-EXE Installer | Self-extracting setup with embedded payload |
| | UAC Admin Install | Proper certificate installation with elevation |
| | Auto Python Setup | Downloads Python 3.11 if missing |
| | Desktop Shortcuts | Start Menu + Desktop + Startup integration |

</details>

<br />

## 🚀 Quick Start

### Prerequisites

| Requirement | Minimum | Recommended |
|:---|:---|:---|
| **OS** | Windows 10 64-bit | Windows 11 |
| **Python** | 3.10 | 3.11 or 3.12 |
| **GPU** | Any NVIDIA with CUDA | RTX 3060+ (8GB+ VRAM) |
| **RAM** | 16 GB | 32 GB |
| **Storage** | 10 GB free | SSD recommended |

### Option A: Single-EXE Installer *(Recommended)*

```powershell
# Download and run — that's it.
.\DarkMaxxerSetup.exe
```

The installer handles everything automatically:

```
 ✅  UAC elevation for certificate installation
 ✅  SMXF certificate → LocalMachine\Root + TrustedPublisher
 ✅  Python 3.11 bootstrap (if not installed)
 ✅  Virtual environment + pip dependency installation
 ✅  Desktop shortcut + Start Menu entry
 ✅  Windows Defender exclusion
 ✅  Mark-of-the-Web (Zone.Identifier) removal
```

### Option B: Developer Setup

```powershell
git clone https://github.com/Vikalp-Sharma/DarkMaxxer.git
cd DarkMaxxer
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### First Launch

```powershell
.\DarkMaxxer.exe    # From install directory
# or
python main.py      # From source
```

> **📌 On first startup:** A centered splash screen displays for 5 seconds while the engine initializes. You'll then be prompted to select a local AI model folder or weight file (`.gguf`, `.safetensors`, `.bin`, `.pth`).

<br />

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DARKMAXXER GUI  (Chromium / WebView)             │
│  ┌───────────────┐  ┌──────────────────┐  ┌──────────────────────┐ │
│  │   Explorer     │  │   Nebula Chat    │  │    Terminal          │ │
│  │   File Tree    │  │   + Starfield    │  │    Streaming Logs    │ │
│  └───────┬───────┘  └────────┬─────────┘  └──────────┬───────────┘ │
└──────────┼───────────────────┼───────────────────────┼─────────────┘
           │                   │                       │
           ▼                   ▼                       ▼
┌─────────────────────────────────────────────────────────────────────┐
│              PYTHON BRIDGE API  (main.py / pywebview)               │
│                                                                     │
│  ┌─────────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ memory_manager  │ │  llm_engine  │ │    mcp_integration       │ │
│  │  ─ Chats        │ │  ─ AirLLM    │ │  ─ FileOpsServer (local) │ │
│  │  ─ Config       │ │  ─ GGUF      │ │  ─ MCPClient (external)  │ │
│  │  ─ State        │ │  ─ HF Router │ │  ─ JSON-RPC over stdio   │ │
│  └─────────────────┘ └──────┬───────┘ └──────────────────────────┘ │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              HARDWARE EXECUTION LAYER  (CUDA / System)              │
│                                                                     │
│   GPU VRAM ◄══ Layer-by-Layer Dynamic Offloading (AirLLM) ══► RAM  │
│                                                                     │
│   ┌─ Layer 0 ──► GPU ──► Output ──► Unload ──► Layer 1 ──► ... ─┐ │
│   └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

<br />

## 💾 Supported Models

DarkMaxxer's hybrid routing engine automatically detects model format and selects the optimal inference backend:

### Formats

| Format | Engine | Best For | Examples |
|:---|:---|:---|:---|
| **AirLLM** | Layer-wise offloading | 70B+ models on consumer GPUs | `Llama-3-70B`, `Platypus2-70B`, `Mixtral-8x7B` |
| **GGUF** | Native quantized loader | Fast inference on mid-range GPUs | `Llama-3-8B-Q4_K_M.gguf`, `Phi-3-mini-Q5.gguf` |
| **HuggingFace** | Transformers + Accelerate | Custom fine-tuned weights | `.safetensors`, `.bin`, `.pth` checkpoints |

### Hardware Requirements

| Model Size | Traditional VRAM | **DarkMaxxer VRAM** | System RAM |
|:---|:---:|:---:|:---:|
| 7B - 8B | 16 GB | **4 - 6 GB** | 16 GB |
| 13B - 14B | 28 GB | **6 - 8 GB** | 16 GB |
| 34B - 40B | 70 GB | **8 - 10 GB** | 32 GB |
| **70B - 72B** | **140+ GB** | **8 - 12 GB** ⚡ | 32 - 64 GB |

<br />

## 🛠 Autonomous Tool Protocols

### Built-in File Operations

The AI autonomously manages your workspace through structured tool calls:

```
User: Create a Flask web server and save it as app.py

DarkMaxxer AI: I'll create a Flask web server for you right now.

[TOOL: CREATE_FILE app.py
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "DarkMaxxer IDE Active!"

if __name__ == '__main__':
    app.run(port=5000)
]

✅ Created: app.py
```

| Tool | Syntax | Description |
|:---|:---|:---|
| `CREATE_FILE` | `[TOOL: CREATE_FILE path\ncontent]` | Create new files |
| `EDIT_FILE` | `[TOOL: EDIT_FILE path\ncontent]` | Overwrite existing files |
| `READ_FILE` | `[TOOL: READ_FILE path]` | Read file contents into context |
| `DELETE_FILE` | `[TOOL: DELETE_FILE path]` | Remove files from workspace |
| `RENAME_FILE` | `[TOOL: RENAME_FILE old_path new_path]` | Rename/move files |
| `APPEND_FILE` | `[TOOL: APPEND_FILE path\ncontent]` | Append content to files |

### External MCP Servers

Connect any MCP-compatible server from **Settings → MCP Servers**:

```json
{
  "name": "github-mcp",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": { "GITHUB_TOKEN": "ghp_..." }
}
```

The AI discovers tools automatically and calls them via:
```
[TOOL: MCP_CALL server=github-mcp tool=search_repositories args={"query": "darkmaxxer"}]
```

<br />

## 📂 Project Structure

```
DarkMaxxer/
├── main.py                 # Application controller & PyWebView bridge
├── llm_engine.py           # AI router: AirLLM + GGUF + HuggingFace
├── memory_manager.py       # Persistent storage: chats, config, state
├── mcp_integration.py      # File ops server + external MCP client
├── requirements.txt        # Python dependencies
├── config.json             # Runtime configuration
├── LICENSE                 # Proprietary license
├── README.md               # You are here
│
├── gui/                    # Frontend (Chromium WebView)
│   ├── index.html          # Main IDE workspace & chat
│   ├── settings.html       # Configuration & MCP management
│   ├── models.html         # Model loading center
│   ├── splash.html         # Startup splash screen
│   └── logo.png            # Application logo
│
└── DarkEXE/                # Build & distribution
    ├── build_exe.py         # PyInstaller build + SMXF code-signing
    ├── setup_engine.py      # Installer UI + cert install + Python bootstrap
    ├── launcher.py          # EXE launcher & subprocess manager
    ├── DarkMaxxer.manifest  # Windows app manifest (DPI, compatibility)
    ├── SMXF.cer             # Code-signing certificate
    └── logo.ico             # Application icon
```

<br />

## ❓ FAQ

<details>
<summary><b>How does DarkMaxxer run 70B models on a 8GB GPU?</b></summary>

<br />

AirLLM's layer-wise offloading works by loading **one transformer layer at a time** into GPU VRAM, running the forward pass, then swapping it out for the next layer. This means your peak VRAM usage equals the size of the single largest layer (~200MB - 1GB) rather than the entire model (~140GB). The tradeoff is speed — inference is slower than having the full model in VRAM — but it makes previously impossible model sizes accessible on consumer hardware.
</details>

<details>
<summary><b>Is my code really 100% private?</b></summary>

<br />

Yes. DarkMaxxer makes **zero network calls** during operation. There are no telemetry endpoints, no usage analytics, no crash reporters, and no "phone home" features. The AI model runs entirely in your local GPU/CPU. Your code never leaves your machine. You can verify this by running it with your network adapter disabled.
</details>

<details>
<summary><b>Can I pause/cancel the AI mid-generation?</b></summary>

<br />

Yes. Click the glowing **⏸ Pause** button in the chat bar. This sends an async interruption signal (`cancel_generation`) to the inference thread, halting it within the current token step and freeing GPU compute immediately.
</details>

<details>
<summary><b>How do I connect external MCP servers?</b></summary>

<br />

Go to **Settings → MCP Servers → Add Server**. Enter the server name, command (e.g., `npx`), arguments (e.g., `-y @modelcontextprotocol/server-github`), and any environment variables. Click "Save & Connect" — the AI will automatically discover available tools and inject them into its system prompt.
</details>

<details>
<summary><b>Why does Smart App Control / SmartScreen block the app?</b></summary>

<br />

DarkMaxxer is code-signed with the SMXF self-signed certificate. The installer (`DarkMaxxerSetup.exe`) requests admin elevation and installs this certificate into your system's `LocalMachine\Root` and `TrustedPublisher` stores. If you're still getting warnings, run the installer first — it handles all certificate trust and Defender exclusions automatically.
</details>

<details>
<summary><b>What tokenizer does DarkMaxxer use for GGUF files?</b></summary>

<br />

DarkMaxxer extracts tokenizer definitions directly from the GGUF header metadata. If the GGUF file contains embedded tokenizer data, it's used natively — no separate `tokenizer.json` needed. For models without embedded tokenizers, it falls back to a compatible tokenizer from the same model family.
</details>

<br />

## 👨‍💻 Author & License

<div align="center">

**Created and maintained by [Vikalp Sharma](https://github.com/Vikalp-Sharma)**

Published by **SMXF**

© 2025-2026 Vikalp Sharma. All rights reserved.

[![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge&labelColor=1a1a2e)](LICENSE)

*Unauthorized distribution, modification, or commercial exploitation is strictly prohibited without explicit written consent. See [`LICENSE`](LICENSE) for complete terms.*

</div>

---

<div align="center">

<sub>

**Built with** [AirLLM](https://github.com/lyogavin/airllm) · [PyWebView](https://pywebview.flowrl.com) · [HuggingFace Transformers](https://huggingface.co) · [PyTorch](https://pytorch.org) · [PyInstaller](https://pyinstaller.org)

*Autonomous. Air-gapped. Dark-mode-first.*

</sub>

</div>
