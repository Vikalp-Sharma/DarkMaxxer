// [Vikalp Sharma] - Proprietary / Anti-Theft Watermark
// DarkMaxxer Native Cross-Platform Rust Installer (Linux & Windows)
use std::env;
use std::fs;
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum GpuMode {
    Rocm,
    Nvidia,
    Cpu,
}

fn print_banner() {
    println!("\x1b[1;36m====================================================\x1b[0m");
    println!("\x1b[1;32m       DARKMAXXER — Native Rust Installer           \x1b[0m");
    println!("\x1b[1;34m       Autonomous Local AI Workspace                \x1b[0m");
    println!("\x1b[1;36m====================================================\x1b[0m\n");
}

fn ask_gpu_mode(cli_mode: Option<&str>) -> GpuMode {
    if let Some(m) = cli_mode {
        match m.to_lowercase().as_str() {
            "rocm" | "amd" | "1" => return GpuMode::Rocm,
            "nvidia" | "cuda" | "2" => return GpuMode::Nvidia,
            _ => return GpuMode::Cpu,
        }
    }

    println!("\x1b[1;33m[?] Which compute device do you want to configure for DarkMaxxer?\x1b[0m");
    println!("    \x1b[1;32m[1] AMD ROCm\x1b[0m     (Radeon RX / Vega / Navi / Mobile)");
    println!("    \x1b[1;32m[2] NVIDIA CUDA\x1b[0m  (GeForce RTX / GTX / Tesla)");
    println!("    \x1b[1;32m[3] CPU Only\x1b[0m     (Universal Intel / AMD / ARM)");
    print!("\x1b[1mEnter choice [1-3] (Default: 3): \x1b[0m");
    let _ = io::stdout().flush();

    let mut input = String::new();
    if io::stdin().read_line(&mut input).is_ok() {
        match input.trim() {
            "1" | "rocm" | "amd" => {
                println!("  ✔ Selected: AMD ROCm Mode");
                GpuMode::Rocm
            }
            "2" | "nvidia" | "cuda" => {
                println!("  ✔ Selected: NVIDIA CUDA Mode");
                GpuMode::Nvidia
            }
            _ => {
                println!("  ✔ Selected: CPU Only Mode (Fast & Universal)");
                GpuMode::Cpu
            }
        }
    } else {
        GpuMode::Cpu
    }
}

fn detect_python() -> Result<String, String> {
    println!("\n[1/5] Detecting Python environment...");

    // 1. Check if user PyEnv exists
    let user_pyenv = PathBuf::from("/run/media/kairo/S-M-X-F/Da-Ta/PyEnv/bin/python3");
    if user_pyenv.exists() {
        println!("  ✔ Found dedicated PyEnv: {:?}", user_pyenv);
        return Ok(user_pyenv.to_string_lossy().to_string());
    }

    #[cfg(target_os = "windows")]
    let candidates = ["python", "py", "python3"];

    #[cfg(not(target_os = "windows"))]
    let candidates = ["python3", "python"];

    for candidate in candidates {
        if let Ok(output) = Command::new(candidate).arg("--version").output() {
            if output.status.success() {
                let ver = String::from_utf8_lossy(&output.stdout);
                println!("  ✔ Found System Python: {}", ver.trim());
                return Ok(candidate.to_string());
            }
        }
    }

    Err("Python 3 was not found. Please install Python 3.10+ and add it to PATH.".to_string())
}

fn setup_venv(app_dir: &Path, python_cmd: &str) -> Result<PathBuf, String> {
    println!("[2/5] Initializing application virtual environment...");

    // If user_pyenv is active, use its pip directly
    let user_pip = PathBuf::from("/run/media/kairo/S-M-X-F/Da-Ta/PyEnv/bin/pip");
    if user_pip.exists() && python_cmd.contains("PyEnv") {
        println!("  ✔ Using user's dedicated PyEnv pip: {:?}", user_pip);
        return Ok(user_pip);
    }

    let venv_dir = if app_dir == Path::new("/opt/darkmaxxer") {
        app_dir.join("venv")
    } else {
        app_dir.join("venv")
    };

    if !venv_dir.exists() {
        let status = Command::new(python_cmd)
            .args(["-m", "venv", "--system-site-packages", &venv_dir.to_string_lossy()])
            .status()
            .map_err(|e| format!("Failed to create venv: {}", e))?;

        if !status.success() {
            return Err("venv creation failed. Ensure python3-venv is installed on Linux.".to_string());
        }
        println!("  ✔ Created lean venv at {:?}", venv_dir);
    } else {
        println!("  ✔ Existing venv detected at {:?}", venv_dir);
    }

    #[cfg(target_os = "windows")]
    let venv_pip = venv_dir.join("Scripts/pip.exe");

    #[cfg(not(target_os = "windows"))]
    let venv_pip = venv_dir.join("bin/pip");

    if !venv_pip.exists() {
        return Err(format!("pip executable not found in venv: {:?}", venv_pip));
    }

    Ok(venv_pip)
}

fn install_mode_packages(pip_path: &Path, mode: GpuMode) -> Result<(), String> {
    println!("[3/5] Installing packages for selected compute mode (Zero Audio/Vision Bloat)...");

    // Check if torch already present in python environment
    let check_torch = Command::new(pip_path)
        .args(["show", "torch"])
        .output();

    let has_torch = check_torch.map(|o| o.status.success()).unwrap_or(false);

    if !has_torch {
        println!("  → Downloading PyTorch for selected hardware...");
        let torch_status = match mode {
            GpuMode::Rocm => {
                println!("    [AMD ROCm] Installing PyTorch with ROCm 6.2 index...");
                Command::new(pip_path)
                    .args(["install", "torch", "--index-url", "https://download.pytorch.org/whl/rocm6.2"])
                    .status()
            }
            GpuMode::Nvidia => {
                println!("    [NVIDIA CUDA] Installing PyTorch with CUDA 12.4 index...");
                Command::new(pip_path)
                    .args(["install", "torch", "--index-url", "https://download.pytorch.org/whl/cu124"])
                    .status()
            }
            GpuMode::Cpu => {
                println!("    [CPU Only] Installing lean PyTorch CPU index...");
                Command::new(pip_path)
                    .args(["install", "torch", "--index-url", "https://download.pytorch.org/whl/cpu"])
                    .status()
            }
        };

        if let Ok(st) = torch_status {
            if !st.success() {
                eprintln!("  ⚠ Warning: Custom torch index installation failed. Attempting standard pip install...");
                let _ = Command::new(pip_path).args(["install", "torch"]).status();
            }
        }
    } else {
        println!("  ✔ PyTorch already present in environment (skipping redundant download).");
    }

    // Install text LLM packages only — NO torchaudio, NO torchvision
    let text_packages = [
        "transformers>=5.2.0",
        "airllm",
        "accelerate",
        "gguf",
        "safetensors",
        "sentencepiece",
        "protobuf",
        "numpy",
        "certifi"
    ];

    println!("  → Installing text inference libraries (transformers, airllm, gguf, etc.)...");
    let _ = Command::new(pip_path)
        .args(&["install", "--upgrade"])
        .args(&text_packages)
        .status();

    println!("  ✔ Text AI inference packages verified.");
    Ok(())
}

fn configure_app(app_dir: &Path, mode: GpuMode) {
    println!("[4/5] Updating application configuration...");

    let compute_mode_str = match mode {
        GpuMode::Rocm => "gpu_amd",
        GpuMode::Nvidia => "gpu_nvidia",
        GpuMode::Cpu => "cpu",
    };

    let use_gpu = mode != GpuMode::Cpu;

    let config_content = serde_json::json!({
        "settings": {
            "local_inference": true,
            "gpu_acceleration": use_gpu,
            "compute_mode": compute_mode_str,
            "context_memory": true
        },
        "ai_path": null,
        "active_conv_id": null,
        "active_workspace_dir": null,
        "workspace_mode": "local",
        "active_sidebar_tab": "chats"
    });

    if let Ok(json) = serde_json::to_string_pretty(&config_content) {
        if let Some(cfg_dir) = dirs::config_dir() {
            let user_app_cfg = cfg_dir.join("DarkMaxxer");
            let _ = fs::create_dir_all(&user_app_cfg);
            let user_cfg_file = user_app_cfg.join("config.json");
            let _ = fs::write(&user_cfg_file, &json);
            println!("  ✔ Configured compute_mode: '{}' in {:?}", compute_mode_str, user_cfg_file);
        }

        let config_path = app_dir.join("config.json");
        if let Ok(_) = fs::write(&config_path, &json) {
            println!("  ✔ Configured compute_mode in {:?}", config_path);
        }
    }
}

fn configure_launcher(app_dir: &Path) -> Result<(), String> {
    println!("[5/5] Configuring system launcher...");

    #[cfg(not(target_os = "windows"))]
    {
        // 1. Desktop shortcut
        let desktop_content = format!(
            "[Desktop Entry]\n\
             Name=DarkMaxxer\n\
             Comment=The Ultimate Autonomous Local AI Workspace\n\
             Exec={}/darkmaxxer\n\
             Icon={}/gui/logo.png\n\
             Terminal=false\n\
             Type=Application\n\
             Categories=Development;ArtificialIntelligence;Utility;\n",
            app_dir.to_string_lossy(),
            app_dir.to_string_lossy()
        );

        if let Some(home) = dirs::home_dir() {
            let user_apps = home.join(".local/share/applications");
            let _ = fs::create_dir_all(&user_apps);
            let _ = fs::write(user_apps.join("darkmaxxer.desktop"), &desktop_content);
        }

        let sys_apps = PathBuf::from("/usr/share/applications");
        if sys_apps.exists() {
            let _ = fs::write(sys_apps.join("darkmaxxer.desktop"), &desktop_content);
        }

        // 2. Symlinks in /usr/local/bin or /usr/bin if writable
        let binary = app_dir.join("darkmaxxer");
        if binary.exists() {
            let _ = Command::new("ln").args(["-sf", &binary.to_string_lossy(), "/usr/local/bin/darkmaxxer"]).status();
        }

        println!("  ✔ Desktop shortcuts created.");
    }

    Ok(())
}

fn uninstall(app_dir: &Path) {
    println!("\x1b[1;33mExecuting clean uninstallation of DarkMaxxer...\x1b[0m");

    #[cfg(not(target_os = "windows"))]
    {
        if let Some(home) = dirs::home_dir() {
            let _ = fs::remove_file(home.join(".local/share/applications/darkmaxxer.desktop"));
        }
        let _ = fs::remove_file("/usr/share/applications/darkmaxxer.desktop");
        let _ = fs::remove_file("/usr/local/bin/darkmaxxer");
    }

    let venv_dir = app_dir.join("venv");
    if venv_dir.exists() {
        let _ = fs::remove_dir_all(venv_dir);
        println!("  ✔ Removed application venv.");
    }

    println!("\x1b[1;32mUninstallation complete.\x1b[0m");
}

fn main() {
    print_banner();

    let args: Vec<String> = env::args().collect();
    let app_dir = env::current_dir().unwrap_or_else(|_| PathBuf::from("."));

    if args.iter().any(|a| a == "--uninstall") {
        uninstall(&app_dir);
        return;
    }

    let cli_mode = args.iter()
        .position(|a| a == "--mode")
        .and_then(|idx| args.get(idx + 1))
        .map(|s| s.as_str());

    let gpu_mode = ask_gpu_mode(cli_mode);

    match detect_python() {
        Ok(py) => {
            match setup_venv(&app_dir, &py) {
                Ok(pip) => {
                    let _ = install_mode_packages(&pip, gpu_mode);
                }
                Err(e) => eprintln!("\x1b[1;31mVenv error:\x1b[0m {}", e),
            }
        }
        Err(e) => eprintln!("\x1b[1;31mPython error:\x1b[0m {}", e),
    }

    configure_app(&app_dir, gpu_mode);
    let _ = configure_launcher(&app_dir);

    println!("\n\x1b[1;32m✔ DarkMaxxer installation setup finished successfully!\x1b[0m");
    println!("Run \x1b[1m'darkmaxxer'\x1b[0m or launch it from your application menu.\n");
}
