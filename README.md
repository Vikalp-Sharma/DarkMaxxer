<div align="center">

```
██████╗  █████╗ ██████╗ ██╗  ██╗███╗   ███╗ █████╗ ██╗  ██╗██╗  ██╗███████╗██████╗ 
██╔══██╗██╔══██╗██╔══██╗██║ ██╔╝████╗ ████║██╔══██╗╚██╗██╔╝╚██╗██╔╝██╔════╝██╔══██╗
██║  ██║███████║██████╔╝█████╔╝ ██╔████╔██║███████║ ╚███╔╝  ╚███╔╝ █████╗  ██████╔╝
██║  ██║██╔══██║██╔══██╗██╔═██╗ ██║╚██╔╝██║██╔══██║ ██╔██╗  ██╔██╗ ██╔══╝  ██╔══██╗
██████╔╝██║  ██║██║  ██║██║  ██╗██║ ╚═╝ ██║██║  ██║██╔╝ ██╗██╔╝ ██╗███████╗██║  ██║
╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
```

### **The Ultimate Local AI Coding & Agentic IDE for Windows**

*Run 70B+ Parameter Language Models Locally on Normal Hardware via Layer-Wise GPU Offloading.*

[![Version](https://img.shields.io/badge/Version-v2.5.0--pro-purple.svg?style=for-the-badge&logo=appveyor)](https://github.com/Vikalp-Sharma/DarkMaxxer)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6.svg?style=for-the-badge&logo=windows)](https://github.com/Vikalp-Sharma/DarkMaxxer)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Engine](https://img.shields.io/badge/Inference%20Engine-AirLLM%20%2F%20GGUF-FF6F00.svg?style=for-the-badge&logo=pytorch&logoColor=white)](https://github.com/lyogavin/airllm)
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Offline%20%2F%20No%20Telemetry-10B981.svg?style=for-the-badge&logo=shield)](https://github.com/Vikalp-Sharma/DarkMaxxer)
[![Author](https://img.shields.io/badge/Author-Vikalp%20Sharma-E10098.svg?style=for-the-badge&logo=github)](https://github.com/Vikalp-Sharma)

---

</div>

## 🌌 Overview

**DarkMaxxer** is a state-of-the-art, local-first Windows Desktop IDE designed from the ground up for agentic AI workflows. While traditional IDEs rely on cloud APIs (Leaking your code, requiring expensive subscriptions, and introducing latency), DarkMaxxer runs **entirely on your local hardware**. 

By leveraging **AirLLM's Layer-Wise GPU Offloading Engine** alongside native HuggingFace and GGUF quantization pipelines, DarkMaxxer allows consumer GPUs to execute 70B+ parameter AI models that would normally require upwards of 140GB of VRAM. It pairs this immense local power with a **secure Model Context Protocol (MCP) file sandbox**, allowing the AI to autonomously create, edit, read, and delete code files right in your workspace.

---

## 🔥 Key Features

| Feature | Description |
| :--- | :--- |
| **⚡ Layer-Wise Offloading** | Powered by `airllm`, dynamically loading and unloading individual neural layers between GPU VRAM and System RAM/Disk mid-inference. Run 70B models on 8GB/16GB VRAM GPUs! |
| **🔒 100% Air-Gapped & Private** | Zero cloud calls. Zero API keys. Zero telemetry. Your codebase, proprietary algorithms, and conversation histories never leave your personal computer. |
| **🛠️ Autonomous Agentic Workspace** | The AI doesn't just chat—it *codes*. It emits structured tool calls (`CREATE_FILE`, `EDIT_FILE`, `DELETE_FILE`, `READ_FILE`) to interact with your live workspace in real time. |
| **🎨 Glassmorphic Nebula UI** | Built with chromium-backed `pywebview` and custom design system (`Stitch`), featuring dynamic starfields, glowing nebula gradients, and responsive micro-animations. |
| **🖥️ Live Multi-Window Terminal** | Real-time streaming logs of model loading, tensor transformations, shell executions, and system diagnostics. Features instant pop-out modal toggling (`toggleTerminalPopout`). |
| **🧠 Persistent Context & State** | Never lose your train of thought. Navigating between workspace tabs, explorer views, or settings menus preserves all DOM state and chat history cleanly (`restoreState`). |
| **⏸️ Real-Time Interruption** | Instant **Pause Generation** functionality (`cancel_generation`), letting you halt long multi-token reasoning chains instantly and redirect the AI mid-thought. |

---

## 🏗️ System Architecture

DarkMaxxer operates using a clean, decoupled bridge architecture combining a high-performance Python local inference server with an ultra-responsive Chromium web interface:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          DARKMAXXER GUI (Chromium / Webview)                    │
│  ┌──────────────────────┐  ┌─────────────────────────┐  ┌────────────────────┐  │
│  │  Sidebar Explorer    │  │  Nebula Chat / Starfield│  │  Terminal Output   │  │
│  └──────────┬───────────┘  └────────────┬────────────┘  └─────────┬──────────┘  │
└─────────────┼───────────────────────────┼─────────────────────────┼─────────────┘
              │                           │                         │
              ▼                           ▼                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      PYTHON BRIDGE API (main.py / pywebview)                    │
│  ┌──────────────────────┐  ┌─────────────────────────┐  ┌────────────────────┐  │
│  │   memory_manager.py  │  │    llm_engine.py        │  │ mcp_integration.py │  │
│  │ (Chats, Logs, State) │  │ (AirLLM / GGUF Router)  │  │ (Sandboxed Files)  │  │
│  └──────────────────────┘  └────────────┬────────────┘  └────────────────────┘  │
└─────────────────────────────────────────┼───────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                       HARDWARE EXECUTION LAYER (CUDA / System)                  │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │   GPU VRAM <== (Layer-by-Layer Dynamic Offloading via AirLLM) ==> RAM/Disk│  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
* **Operating System:** Windows 10 or Windows 11 (64-bit)
* **Python Runtime:** Python 3.10, 3.11, or 3.12 (`python --version`)
* **Hardware:** NVIDIA GPU with CUDA drivers installed (Recommended for fast inference, though CPU fallback is supported)

### 2. Installation & Setup (Single Master Installer)
DarkMaxxer is distributed as a **Single Master Self-Extracting Executable (`DarkMaxxerSetup.exe`)** that embeds all project data, GUI assets, and offline dependencies cleanly inside one file:

```powershell
# Option A: Run the Single Master Standalone Installer (Recommended for End Users)
.\DarkMaxxerSetup.exe
```

**What the Installer Does Automatically:**
1. **Destination Browse & Folder Creation:** Lets you choose any install location (e.g. `C:\Program Files` or `D:\Apps`) and automatically creates a `DarkMaxxer` folder inside it.
2. **System Python Verification / Bootstrap:** Checks for Python 3.10+. If missing on the user's system, silently downloads and installs official lightweight Python 3.11 automatically.
3. **Pip & Dependency Installation:** Installs required packages (`airllm`, `pywebview`, `torch`, `transformers`, `pillow`) while showing a **live loading progress bar**.
4. **Shortcuts & Start Menu:** Creates a **DarkMaxxer** Start Menu folder, Desktop Shortcut, and Windows Startup Menu entry (`Shell:Startup`) formatted with `logo.png` (`gui/logo.png`).
5. **LocalLow Data Initialization:** Pre-creates `%LOCALAPPDATA%Low\DarkMaxxer` storage for models, history, and cache.

```powershell
# Option B: Manual Virtual Environment Setup (For Developers)
git clone https://github.com/Vikalp-Sharma/DarkMaxxer.git
cd DarkMaxxer
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### 3. Launching the IDE
Once installed via `DarkMaxxerSetup.exe`, double-click **DarkMaxxer** on your Desktop, Start Menu, or run directly:

```powershell
# Launch installed Executable inside destination directory
.\DarkMaxxer.exe

# Or run from source
python main.py
```

> **Note:** On first startup, DarkMaxxer will prompt you to select a local AI model folder or weight file (`.gguf`, `.safetensors`, `.bin`, `.pth`) from your disk before entering the workspace. Remote model downloading is disabled per strict offline local security policy.

---

## 📂 Project Directory Structure

```text
DarkMaxxer/
├── 🚀 DarkMaxxerSetup.exe  # Standalone Master Self-Extracting Windows Setup Wizard (Single Exe holding all data)
├── 📄 main.py              # Primary Application Controller & PyWebView JS-to-Python Bridge
├── 📄 llm_engine.py        # Core AI Router: AirLLM Layer-Wise Offloading & Local GGUF/HF Loader
├── 📄 memory_manager.py    # Persistent Storage Engine for Conversations, Tokens & User Configs
├── 📄 mcp_integration.py   # Secure File Operations & Workspace Sandbox Protocol
├── 📄 requirements.txt     # Python Pinned Dependencies (Torch, AirLLM, PyWebView, etc.)
├── 📜 LICENSE              # Proprietary Software License Agreement
├── 📁 DarkEXE/             # Build Engine & Executable Packaging Configuration
│   ├── 📄 setup_engine.py  # First-Run Installer UI & Pip Environment Bootstrapper
│   ├── 📄 launcher.py      # Executable Launcher & Subprocess Supervisor
│   ├── 📄 build_exe.py     # Automated PyInstaller & Inno Setup Build Script
│   ├── 📦 installer.iss    # Inno Setup Windows Compilation Script (.exe creation)
│   └── 🎨 logo.ico         # High-Resolution Windows Application & Taskbar Icon
└── 📁 gui/                 # Frontend Webview Assets & Chromium UI
    ├── 🌐 index.html       # Main IDE Workspace & Chat Interface
    ├── ⚙️ settings.html    # Configuration & Engine Settings Dashboard
    ├── 🧩 models.html      # Model Management & Loading Center
    └── 🎨 logo.png         # Primary Branding Logo & UI Asset
```

---

## 💾 Storage & Data Persistence

DarkMaxxer stores zero files in system temp paths. All user workspace states, chat histories, active configuration files, and IDE states are cleanly organized inside your local AppData directory:

```text
C:\Users\<YourUsername>\AppData\Roaming\.DarkMaxxer\
├── 📄 config.json                      # IDE Global Preferences, Active Paths & UI Theme
├── 📁 Context/                         # Persistent Chat Histories & Conversation Threads
│   └── <conversation_id>/
│       ├── 📄 metadata.json            # Thread Title, Created Timestamp, Active Model ID
│       └── 📄 history.json             # Complete Turn-by-Turn Message Logs & Tool Execution Records
└── 📁 Minds/                           # Dedicated Sandboxed Working Directories per Conversation
    └── <conversation_id>/
        └── <workspace_files>           # Autonomous Files Created/Edited by the AI
```

---

## 🤖 Supported Models & Hardware Requirements

DarkMaxxer's hybrid routing engine automatically detects what model format you provide and routes it through the appropriate high-performance inference backend:

### **Model Formats Supported**
1. **AirLLM Layer-Wise Offloading (`AutoModel.from_pretrained`)**
   * *Best For:* Massive enterprise-grade models (70B+) on consumer GPUs.
   * *Examples:* `garage-bAInd/Platypus2-70B-instruct`, `meta-llama/Llama-3-70B-Instruct`, `mistralai/Mixtral-8x7B-Instruct-v0.1`
2. **GGUF / Quantized Weights (`AutoTokenizer + AutoModelForCausalLM`)**
   * *Best For:* High-speed local inference on mid-range GPUs (8GB - 16GB VRAM).
   * *Examples:* `Llama-3-8B-Instruct.Q4_K_M.gguf`, `Phi-3-mini-4k-instruct-Q5_K_M.gguf`
3. **Native HuggingFace Transformers / PyTorch Binaries (`.pth`, `.pt`, `.bin`, `.safetensors`)**
   * *Best For:* Custom fine-tuned weights and raw checkpoint files.

### **Hardware Matrix**

| Model Class | Traditional VRAM Needed | **DarkMaxxer VRAM Needed** | Recommended RAM |
| :--- | :--- | :--- | :--- |
| **7B - 8B Parameters** | 16 GB | **4 GB - 6 GB** | 16 GB |
| **13B - 14B Parameters** | 28 GB | **6 GB - 8 GB** | 16 GB |
| **34B - 40B Parameters** | 70 GB | **8 GB - 10 GB** | 32 GB |
| **70B - 72B Parameters** | 140+ GB | **8 GB - 12 GB** *(via AirLLM)* | 32 GB - 64 GB |

---

## 🛠️ Autonomous Tool Protocols (MCP)

When interacting with the AI, DarkMaxxer equips the LLM with direct execution privileges over the current active workspace. The model communicates via exact, deterministic tool-calling payloads:

```markdown
User: Create a simple Python web server using Flask and save it as app.py.

DarkMaxxer AI: I will create your Flask web server immediately.
[TOOL: CREATE_FILE app.py
from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "DarkMaxxer IDE Active!"

if __name__ == '__main__':
    app.run(port=5000)
]
```

* **`[TOOL: CREATE_FILE path content]`** — Instantiates new code files in the active directory.
* **`[TOOL: EDIT_FILE path content]`** — Replaces or modifies existing files with updated code.
* **`[TOOL: READ_FILE path]`** — Reads entire file contents into the AI's short-term context.
* **`[TOOL: DELETE_FILE path]`** — Safely removes files from the current workspace sandbox.

---

## ❓ Frequently Asked Questions (FAQ)

<details>
<summary><b>Q: Why does the terminal pop-out window disappear when navigating tabs?</b></summary>
<p><b>A:</b> DarkMaxxer uses a single-window Chromium DOM injected by Python (`pywebview`). When switching tabs or opening settings, the application state is persisted to Python memory via <code>memory_manager.py</code> and immediately re-hydrated cleanly upon navigation via the <code>restoreState()</code> lifecycle hook.</p>
</details>

<details>
<summary><b>Q: How does the AI know how to use my exact GGUF tokenizer without crashing?</b></summary>
<p><b>A:</b> DarkMaxxer specifically inspects the local directory for matching <code>config.json</code> and vocabulary mappings. If you load a raw GGUF file, the engine automatically extracts the tokenizer definitions natively from the GGUF header rather than forcing generic fallbacks, guaranteeing zero token hallucinations or <code>[?]</code> character corruptions.</p>
</details>

<details>
<summary><b>Q: Can I pause or cancel the AI while it is generating a long code block?</b></summary>
<p><b>A:</b> Yes! Click the glowing red <b>⏸ Pause</b> button right inside the chat bar. This dispatches an asynchronous interruption signal (`cancel_generation`) to the Python generation thread, halting inference cleanly within the current token step and freeing up GPU compute immediately.</p>
</details>

---

## 👨‍💻 Author & License

**Created and Maintained by [Vikalp Sharma](https://github.com/Vikalp-Sharma)**

* **Copyright:** © 2026 Vikalp Sharma. All rights reserved.
* **License:** Proprietary and Confidential. Unauthorized distribution, modification, or commercial exploitation is strictly prohibited without explicit written consent from the author. See [`LICENSE`](LICENSE) for complete terms.

---

<div align="center">
  <p font-size="small">
    Powered by <b>AirLLM</b>, <b>HuggingFace</b>, and <b>PyWebView</b>. <br>
    Built with passion for autonomous, air-gapped, dark-mode-first engineering.
  </p>
</div>
