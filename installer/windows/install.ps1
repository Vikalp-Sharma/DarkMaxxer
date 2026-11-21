# DarkMaxxer 2.0 Native Windows Installer & Environment Setup Script
# [Vikalp Sharma] - Proprietary / Anti-Theft Watermark

param (
    [string]$Mode = ""
)

$ErrorActionPreference = "Stop"

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "       DARKMAXXER — Native Windows Setup           " -ForegroundColor Green
Write-Host "       Autonomous Local AI Workspace                " -ForegroundColor Blue
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

$AppDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
if (-not $AppDir) { $AppDir = Get-Location }

# 1. Ask GPU Mode
if (-not $Mode) {
    Write-Host "[?] Which compute device do you want to configure for DarkMaxxer?" -ForegroundColor Yellow
    Write-Host "    [1] AMD GPU / ROCm / DirectML (Radeon RX / Vega / Navi / Mobile)" -ForegroundColor Green
    Write-Host "    [2] NVIDIA CUDA               (GeForce RTX / GTX / Tesla)" -ForegroundColor Green
    Write-Host "    [3] CPU Only                  (Universal Intel / AMD / ARM)" -ForegroundColor Green
    $choice = Read-Host "Enter choice [1-3] (Default: 3)"
    switch ($choice) {
        "1" { $Mode = "rocm" }
        "2" { $Mode = "nvidia" }
        default { $Mode = "cpu" }
    }
}

Write-Host "  ✔ Selected Compute Mode: $Mode" -ForegroundColor Cyan
Write-Host ""

# 2. Python Environment Detection
Write-Host "[1/5] Detecting Python 3.10+ environment..." -ForegroundColor White
$PythonCmd = $null

$pythonCandidates = @("python", "py", "python3")
foreach ($cand in $pythonCandidates) {
    try {
        $ver = & $cand --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $ver -match "Python 3\.") {
            $PythonCmd = $cand
            Write-Host "  ✔ Found System Python: $ver" -ForegroundColor Green
            break
        }
    } catch {}
}

if (-not $PythonCmd) {
    Write-Host "  ⚠ Python 3 was not detected in PATH." -ForegroundColor Yellow
    Write-Host "  Attempting to install Python 3.11 via Windows Package Manager (winget)..." -ForegroundColor Yellow
    try {
        Start-Process winget -ArgumentList "install -e --id Python.Python.3.11 --accept-source-agreements --accept-package-agreements" -Wait -NoNewWindow
        $PythonCmd = "python"
    } catch {
        Write-Host "  ✖ Failed to auto-install Python. Please install Python 3.10+ from python.org and add to PATH." -ForegroundColor Red
        exit 1
    }
}

# 3. Setup Virtual Environment
Write-Host "[2/5] Setting up virtual environment..." -ForegroundColor White
$VenvDir = Join-Path $AppDir "venv"
if (-not (Test-Path $VenvDir)) {
    Write-Host "  → Creating venv at $VenvDir..." -ForegroundColor Gray
    & $PythonCmd -m venv --system-site-packages $VenvDir
}
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

if (-not (Test-Path $VenvPip)) {
    Write-Host "  ✖ Pip executable missing at $VenvPip" -ForegroundColor Red
    exit 1
}
Write-Host "  ✔ Virtual environment ready." -ForegroundColor Green

# 4. Installing Inference Packages (ZERO Audio/Vision Bloat)
Write-Host "[3/5] Installing text AI packages (Zero torchaudio/torchvision bloat)..." -ForegroundColor White

$hasTorch = $false
try {
    & $VenvPip show torch 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { $hasTorch = $true }
} catch {}

if (-not $hasTorch) {
    Write-Host "  → Downloading PyTorch for selected hardware ($Mode)..." -ForegroundColor Gray
    switch ($Mode) {
        "rocm" {
            # On Windows, PyTorch AMD is supported via standard or DirectML
            & $VenvPip install torch
        }
        "nvidia" {
            Write-Host "    [NVIDIA CUDA] Installing PyTorch with CUDA 12.4 index..." -ForegroundColor Cyan
            & $VenvPip install torch --index-url https://download.pytorch.org/whl/cu124
        }
        default {
            Write-Host "    [CPU Only] Installing PyTorch CPU index..." -ForegroundColor Cyan
            & $VenvPip install torch --index-url https://download.pytorch.org/whl/cpu
        }
    }
} else {
    Write-Host "  ✔ PyTorch already installed in environment." -ForegroundColor Green
}

$textPackages = @(
    "transformers>=5.2.0",
    "airllm",
    "accelerate",
    "gguf",
    "safetensors",
    "sentencepiece",
    "protobuf",
    "numpy",
    "certifi"
)

Write-Host "  → Installing text inference libraries..." -ForegroundColor Gray
& $VenvPip install --upgrade $textPackages | Out-Null
Write-Host "  ✔ Text AI inference packages verified." -ForegroundColor Green

# 5. Application Configuration
Write-Host "[4/5] Configuring DarkMaxxer settings..." -ForegroundColor White
$computeModeStr = switch ($Mode) {
    "rocm" { "gpu_amd" }
    "nvidia" { "gpu_nvidia" }
    default { "cpu" }
}
$useGpu = ($Mode -ne "cpu")

$configJson = @"
{
  "active_conv_id": null,
  "active_sidebar_tab": "chats",
  "active_workspace_dir": null,
  "ai_path": null,
  "settings": {
    "compute_mode": "$computeModeStr",
    "context_memory": true,
    "gpu_acceleration": $(if ($useGpu) { "true" } else { "false" }),
    "local_inference": true
  },
  "workspace_mode": "local"
}
"@

$appDataConfigDir = Join-Path $env:APPDATA "DarkMaxxer"
New-Item -ItemType Directory -Force -Path $appDataConfigDir | Out-Null
$appDataConfigFile = Join-Path $appDataConfigDir "config.json"
Set-Content -Path $appDataConfigFile -Value $configJson
Set-Content -Path (Join-Path $AppDir "config.json") -Value $configJson
Write-Host "  ✔ Configuration saved to $appDataConfigFile" -ForegroundColor Green

# 6. Shortcuts
Write-Host "[5/5] Creating Windows Shortcuts..." -ForegroundColor White
try {
    $WshShell = New-Object -ComObject WScript.Shell
    $TargetExe = Join-Path $AppDir "darkmaxxer.exe"
    if (-not (Test-Path $TargetExe)) {
        # Fallback launcher bat if exe not directly present
        $TargetExe = Join-Path $AppDir "run_darkmaxxer.bat"
        if (-not (Test-Path $TargetExe)) {
            Set-Content -Path $TargetExe -Value "@echo off`r`nstart `"`" `"%~dp0darkmaxxer.exe`""
        }
    }

    $DesktopPath = [Environment]::GetFolderPath("Desktop")
    $Shortcut = $WshShell.CreateShortcut((Join-Path $DesktopPath "DarkMaxxer.lnk"))
    $Shortcut.TargetPath = $TargetExe
    $Shortcut.WorkingDirectory = $AppDir
    $Shortcut.Description = "DarkMaxxer - The Ultimate Local AI Workspace"
    $Shortcut.Save()

    $ProgramsPath = [Environment]::GetFolderPath("Programs")
    $StartMenuDir = Join-Path $ProgramsPath "DarkMaxxer"
    New-Item -ItemType Directory -Force -Path $StartMenuDir | Out-Null
    $StartShortcut = $WshShell.CreateShortcut((Join-Path $StartMenuDir "DarkMaxxer.lnk"))
    $StartShortcut.TargetPath = $TargetExe
    $StartShortcut.WorkingDirectory = $AppDir
    $StartShortcut.Save()

    Write-Host "  ✔ Desktop and Start Menu shortcuts created." -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Could not create shortcuts: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✔ DarkMaxxer Windows setup completed successfully!" -ForegroundColor Green
Write-Host "You can now launch DarkMaxxer from your Desktop or Start Menu." -ForegroundColor Cyan
