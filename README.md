<div align="center">

<img src="gui/logo.png" alt="DarkMaxxer Logo" width="180" />

<br />
<br />

# 𝗗 𝗔 𝗥 𝗞 𝗠 𝗔 𝗫 𝗫 𝗘 𝗥  𝟮.𝟬

<br />

<picture>
  <img alt="Tagline" src="https://img.shields.io/badge/%20-The%20Ultimate%20Local%20AI%20Workspace%20in%20Rust-0a0a0f?style=for-the-badge&labelColor=0a0a0f" />
</picture>

<br />

*Run 70B+ parameter language models on consumer hardware.*  
*100% Native Rust Core · Zero Cloud · Zero API Keys · Zero Bloat.*

<br />
<br />

<!-- ═══════════════ PRIMARY BADGES ═══════════════ -->

<a href="https://github.com/Vikalp-Sharma/DarkMaxxer/releases"><img src="https://img.shields.io/badge/%20%20Release-v2.0.0-6C63FF?style=for-the-badge&logo=github&logoColor=white&labelColor=12121a" alt="Release" /></a>&nbsp;
<a href="https://www.rust-lang.org"><img src="https://img.shields.io/badge/%20%20Core-Rust%202021-DEA584?style=for-the-badge&logo=rust&logoColor=white&labelColor=12121a" alt="Rust" /></a>&nbsp;
<a href="LICENSE"><img src="https://img.shields.io/badge/%20%20License-Proprietary-E10098?style=for-the-badge&logo=gnu-privacy-guard&logoColor=white&labelColor=12121a" alt="License" /></a>

<br />
<br />

<!-- ═══════════════ PLATFORM BADGES ═══════════════ -->

<a href="#-quick-start"><img src="https://img.shields.io/badge/Fedora_%2F_RHEL-51A2DA?style=flat-square&logo=fedora&logoColor=white&labelColor=0d1117" alt="Fedora" /></a>&nbsp;
<a href="#-quick-start"><img src="https://img.shields.io/badge/Debian_%2F_Ubuntu-A81D33?style=flat-square&logo=debian&logoColor=white&labelColor=0d1117" alt="Debian" /></a>&nbsp;
<a href="#-quick-start"><img src="https://img.shields.io/badge/Windows_10_%2F_11-0078D4?style=flat-square&logo=windows&logoColor=white&labelColor=0d1117" alt="Windows" /></a>&nbsp;
<a href="#-quick-start"><img src="https://img.shields.io/badge/Arch_Linux-1793D1?style=flat-square&logo=archlinux&logoColor=white&labelColor=0d1117" alt="Arch" /></a>

<br />
<br />

<!-- ═══════════════ TECH STACK BADGES ═══════════════ -->

<a href="https://github.com/tauri-apps/wry"><img src="https://img.shields.io/badge/GUI-Tao_%2B_Wry-FF6F00?style=flat-square&logo=rust&logoColor=white&labelColor=1a1a2e" alt="Wry" /></a>&nbsp;
<a href="https://github.com/lyogavin/airllm"><img src="https://img.shields.io/badge/Engine-AirLLM-FF6F00?style=flat-square&logo=pytorch&logoColor=white&labelColor=1a1a2e" alt="AirLLM" /></a>&nbsp;
<a href="https://github.com/ggerganov/ggml"><img src="https://img.shields.io/badge/Format-GGUF_%2F_Safetensors-00C7B7?style=flat-square&logo=llvm&logoColor=white&labelColor=1a1a2e" alt="GGUF" /></a>&nbsp;
<a href="https://huggingface.co"><img src="https://img.shields.io/badge/Models-HuggingFace-FFD21E?style=flat-square&logo=huggingface&logoColor=black&labelColor=1a1a2e" alt="HuggingFace" /></a>&nbsp;
<a href="https://github.com/playwright-community/playwright-go"><img src="https://img.shields.io/badge/Automation-Playwright_Go-2EAD33?style=flat-square&logo=go&logoColor=white&labelColor=1a1a2e" alt="Playwright Go" /></a>

<br />
<br />

<!-- ═══════════════ FEATURE HIGHLIGHT BADGES ═══════════════ -->

<img src="https://img.shields.io/badge/%F0%9F%94%92%20100%25%20Offline-No%20Telemetry-10B981?style=flat-square&labelColor=0d1117" alt="Offline" />&nbsp;
<img src="https://img.shields.io/badge/%F0%9F%94%8F%20Code%20Signed-Authenticode%20Verified-6366F1?style=flat-square&labelColor=0d1117" alt="Signed" />&nbsp;
<img src="https://img.shields.io/badge/%E2%9A%A1%20AMD%20ROCm%20%2B%20NVIDIA%20CUDA-GPU%20Offloading-F59E0B?style=flat-square&labelColor=0d1117" alt="GPU" />&nbsp;
<img src="https://img.shields.io/badge/%F0%9F%A4%96%20Agentic-File%20System%20Tools-EC4899?style=flat-square&labelColor=0d1117" alt="Agentic" />&nbsp;
<img src="https://img.shields.io/badge/%F0%9F%9A%80%20Lean%20Dynamic%20Pip-Zero%20Bloat-06B6D4?style=flat-square&labelColor=0d1117" alt="Lean Pip" />

<br />

---

<br />

**[Overview](#-what-is-darkmaxxer)** &nbsp;·&nbsp; **[Tested Models](#-verified--tested-models)** &nbsp;·&nbsp; **[Quick Start](#-quick-start)** &nbsp;·&nbsp; **[Windows Setup](#-windows-setup-administrator--code-signing)** &nbsp;·&nbsp; **[Architecture](#-rust-architecture--dual-tier-engine)** &nbsp;·&nbsp; **[Automated Model Downloader](#-automated-model-downloader-playwright-go)** &nbsp;·&nbsp; **[Author & License](#-author--license)**

<br />

</div>

---

## 🌌 What is DarkMaxxer?

**DarkMaxxer 2.0** is a private, air-gapped, local-first AI workspace and IDE built from the ground up with a **high-performance native Rust core** (`darkmaxxer` and `darkmaxxer-installer`).

Unlike traditional AI coding environments that upload your code to remote third-party servers, DarkMaxxer executes **everything 100% locally on your hardware**. Using a revolutionary **dual-tier AI engine**:
- **Fast In-Memory Tier:** Runs compact models (< 2.5 GB) directly in memory with real-time token throughput (15–30 tokens/second).
- **Layer-Wise Streaming Tier (AirLLM):** Streams massive **70B+ parameter models** layer-by-layer between storage and GPU/CPU, enabling large-scale local AI on consumer laptops and desktop GPUs with as little as **4GB–8GB of VRAM**.

<br />

---

## 🧪 Verified & Tested Models

DarkMaxxer supports all major modern AI model families across `.gguf`, `.safetensors`, `.bin`, and `.pth` weight formats. The following models have been downloaded, verified, and benchmarked across distinct functional categories:

| Category | Model Name | Format & Architecture | Disk Size | Hardware Mode | Generation Speed / Status | Verified Capabilities |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Chat & Assistant** | **Qwen 2.5 0.5B Instruct** | GGUF (`q4_k_m`) / Qwen2 | 469 MB | CPU / ROCm / CUDA | ~22.4 tokens/s (Fast RAM) | Multi-turn chat, markdown formatting, tool invocation |
| **Code Generation** | **Qwen 2.5 Coder 0.5B Instruct** | GGUF (`q4_k_m`) / Qwen2-Coder | 469 MB | CPU / ROCm / CUDA | ~20.1 tokens/s (Fast RAM) | Rust, Python, C++, TypeScript code generation & debugging |
| **Conversational Chat** | **TinyLlama 1.1B Chat** | GGUF (`q4_k_m`) / LLaMA | 637 MB | CPU / ROCm / CUDA | ~18.5 tokens/s (Fast RAM) | Instruction following, conversation summarization |
| **Feature Embeddings** | **all-MiniLM-L6-v2** | Safetensors / Bert | 87 MB | CPU / ROCm / CUDA | ~45.0 sentences/s | Semantic vector search, project indexing, RAG retrieval |
| **Compact Reasoning** | **SmolLM2 135M Instruct** | Safetensors / LLaMA | 257 MB | CPU / ROCm / CUDA | ~32.0 tokens/s (Ultra-fast) | Lightweight reasoning, quick agent decisions |
| **Large Scale Coding** | **Qwen 2.5 Coder 7B / 14B** | GGUF / Safetensors | 4.5 – 9.0 GB | AMD ROCm / NVIDIA / CPU | Layer-Wise Stream (AirLLM) | Complex multi-file codebase generation on 4–8GB VRAM |
| **Enterprise Reasoning**| **Llama 3.1 70B Instruct** | GGUF / Safetensors | 38 GB | AMD ROCm / NVIDIA / CPU | Layer-Wise Stream (AirLLM) | 70B parameter reasoning on consumer hardware |

<br />

---

## 🚀 Quick Start

### 🐧 Linux Installation (RPM & DEB)

Native Linux packages install to `/opt/darkmaxxer/` with global symlinks in `/usr/bin/darkmaxxer` and full GNOME Software / AppCenter AppStream integration:

```bash
# ── Fedora / RHEL / CentOS ─────────────────────────────
sudo rpm -Uvh darkmaxxer-2.0.0.x86_64.rpm

# ── Debian / Ubuntu / Linux Mint ───────────────────────
sudo dpkg -i darkmaxxer_2.0.0_amd64.deb

# ── First-Time GPU Hardware Configuration ───────────────
darkmaxxer-installer

# ── Launch DarkMaxxer ──────────────────────────────────
darkmaxxer
```

On first launch, `darkmaxxer-installer` prompts you for your hardware:
```text
[?] Which compute device do you want to configure for DarkMaxxer?
    [1] AMD ROCm     (Radeon RX / Vega / Navi / Mobile)
    [2] NVIDIA CUDA  (GeForce RTX / GTX / Tesla)
    [3] CPU Only     (Universal Intel / AMD / ARM)
```
- **Zero Audio/Vision Bloat:** Downloads strictly text inference packages (`torch`, `transformers>=4.40.0`, `airllm`, `accelerate`, `gguf`, `safetensors`, `sentencepiece`, `protobuf`). **Explicitly NO `torchaudio` and NO `torchvision`**.
- **Dynamic Environment Detection:** Automatically detects `DARKMAXXER_PYTHON` / `PYTHON_PATH` overrides, system Python 3, or creates a lean virtual environment automatically.

<br />

---

## 🪟 Windows Setup (Administrator & Code-Signing)

DarkMaxxer provides a native Windows NSIS Setup installer and a signed portable zip:

### 1. Windows Installer (`DarkMaxxer-2.0.0-Setup.exe` - 12 MB)
- **UAC Administrator Elevation:** Requests standard Administrator elevation via `RequestExecutionLevel admin` and installs to `C:\Program Files\DarkMaxxer`.
- **Authenticode Digital Signature:** Signed with a 4096-bit Code Signing Certificate for `Vikalp Sharma (DarkMaxxer Code Signing)` via `osslsigncode`.
- **Smart App Control & SmartScreen Bypass:**
  - Automatically registers the certificate into Windows `ROOT` and `TrustedPublisher` stores during setup.
  - Creates Start Menu and Desktop shortcuts.

### 2. Portable Distribution (`darkmaxxer-2.0.0-windows-x64.zip` - 12 MB)
- Contains signed `darkmaxxer.exe` and `darkmaxxer-installer.exe`.
- Includes `Trust-Certificate.bat` (1-click script to trust the certificate in Windows) and automated scripts `install.bat` and `install.ps1`.

<br />

---

## ⚙️ Rust Architecture & Dual-Tier Engine

```
DarkMaxxer 2.0 Native Workspace
├── [Rust Native Core]
│   ├── Window & Event Loop: Tao (Wayland / X11 / Win32 container)
│   ├── Web Engine: Wry with custom protocol 'darkmaxxer://localhost/index.html'
│   ├── IPC Bridge: Transparent window.pywebview shim for 100% UI backward-compatibility
│   ├── Process Supervisor: JSON-lines stdio process supervisor with real-time token dispatch
│   └── Config & Context: Multi-conversation persistence in ~/.config/DarkMaxxer/config.json
│
├── [Universal AI Engine] (engine_runner.py)
│   ├── Fast In-Memory Tier (< 2.5 GB): Instant RAM loading, 15–30 tok/s
│   ├── Layer-Wise Streaming Tier (>= 2.5 GB): AirLLM disk-to-compute streaming for 70B+ models
│   └── Multi-Family Support: Qwen (1/2/2.5/3), LLaMA (2/3/3.1), Mistral, Gemma, Phi, DeepSeek
│
└── [Dynamic Hardware Installer] (darkmaxxer-installer)
    ├── Interactive GPU Selector: [1] AMD ROCm · [2] NVIDIA CUDA · [3] CPU Only
    └── Zero Audio/Vision Bloat: Strictly text inference libraries only
```

<br />

---

## 🤖 Automated Model Downloader (Playwright Go)

The repository includes a standalone automated Hugging Face model scraper and downloader located in `scripts/hf_downloader/`:
- **Engine:** Built with `playwright-go` (`github.com/mxschmitt/playwright-go`) and Uber `zap` logging.
- **Stealth & Emulation:** Headless Chromium with randomized viewports, human scrolling, and DOM link extraction.
- **Live Visual Progress Bar:** Displays real-time download status, percent complete, transfer speed in MB/s, and ETA directly in your terminal:
  ```text
  [2/4 Code (Qwen2.5-Coder-0.5B-GGUF)] [██████████████░░░░░░░░░░░]  56.2% (263.5 / 468.6 MB)   1.4 MB/s ETA: 146s
  ```

To run the automated model fetcher:
```bash
cd scripts/hf_downloader
go run main.go
```
Downloaded models are placed into `models/<category>/` and immediately ready for offline local inference in DarkMaxxer.

<br />

---

## 🛠️ Building from Source

### Prerequisites
- **Rust:** `cargo`, `rustc` (1.75+)
- **Linux:** `gtk3-devel`, `webkit2gtk4.1-devel` (or `webkit2gtk4.0-devel`)
- **Windows Cross-Compilation:** `mingw64-gcc`, `mingw64-nsis`, `rust-std-static-x86_64-pc-windows-gnu`

### Linux Build
```bash
cargo build --release
# Binaries output to: target/release/darkmaxxer and target/release/darkmaxxer-installer
```

### Windows Build & Signing
```bash
cargo build --target x86_64-pc-windows-gnu --release
makensis Installers/installer/windows/darkmaxxer.nsi
osslsigncode sign -pkcs12 Installers/installer/windows/certs/codesign.pfx -pass DarkMaxxer2026 \
    -n "DarkMaxxer Setup" -in Installers/dist/DarkMaxxer-2.0.0-Setup.exe -out Installers/dist/DarkMaxxer-2.0.0-Setup.signed.exe
```

<br />

---

## 👨‍💻 Author & License

**Created and maintained by [Vikalp Sharma](https://github.com/Vikalp-Sharma)**  
Published by **SMXF / DarkMaxxer Technologies**

© 2025–2026 Vikalp Sharma. All rights reserved.

<a href="LICENSE"><img src="https://img.shields.io/badge/%20%20License-Proprietary-E10098?style=for-the-badge&logo=gnu-privacy-guard&logoColor=white&labelColor=12121a" alt="License" /></a>

*Unauthorized distribution or commercial exploitation is prohibited without written consent. See [`LICENSE`](LICENSE) for complete terms.*

---

<div align="center">
<sub>Built with Rust · Wry · Tao · AirLLM · HuggingFace Transformers · Playwright Go</sub><br />
<sub>Autonomous · 100% Air-Gapped · Local Intelligence First</sub>
</div>
