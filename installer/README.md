# DarkMaxxer 2.0 Native Installer Suite

This directory contains the native Rust, Linux, and Windows installers for **DarkMaxxer 2.0**:

## Structure
- `main.rs`: Native Rust installer (`darkmaxxer-installer`) with interactive GPU hardware selection (`[1] AMD ROCm`, `[2] NVIDIA CUDA`, `[3] CPU Only`), PyEnv auto-detection, and text-only pip package manager.
- `windows/`:
  - `darkmaxxer.nsi`: Modern NSIS Administrator Installer (`DarkMaxxer-2.0.0-Setup.exe`) installing to `$PROGRAMFILES64\DarkMaxxer`.
  - `certs/`: Authenticode 4096-bit Code Signing Certificate (`codesign.pfx`, `DarkMaxxer.cer`).
  - `Trust-Certificate.bat`: 1-click utility to import the certificate into the Windows Root and TrustedPublisher stores to bypass Windows Smart App Control and SmartScreen.
  - `install.bat` / `install.ps1`: Automated PowerShell and Command Prompt setups.

## CLI Options
Run `darkmaxxer-installer` with optional flags:
- `--mode rocm` / `--mode amd`: Configures AMD ROCm compute.
- `--mode nvidia` / `--mode cuda`: Configures NVIDIA CUDA compute.
- `--mode cpu`: Configures universal CPU compute.
- `--uninstall`: Completely uninstalls DarkMaxxer shortcuts and venv.
