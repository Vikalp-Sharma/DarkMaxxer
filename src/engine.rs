// [Vikalp Sharma] - Proprietary / Anti-Theft Watermark
use serde::{Deserialize, Serialize};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EngineEvent {
    pub event: String,
    #[serde(default)]
    pub message: Option<String>,
    #[serde(default)]
    pub token: Option<String>,
    #[serde(default)]
    pub text: Option<String>,
    #[serde(default)]
    pub success: Option<bool>,
    #[serde(default)]
    pub error: Option<String>,
    #[serde(default)]
    pub model_path: Option<String>,
    #[serde(default)]
    pub device: Option<String>,
    #[serde(default)]
    pub speed_tps: Option<f64>,
    #[serde(default)]
    pub elapsed_sec: Option<f64>,
    #[serde(default)]
    pub result: Option<serde_json::Value>,
}

pub struct EngineSupervisor {
    process: Arc<Mutex<Option<Child>>>,
    stdin_writer: Arc<Mutex<Option<ChildStdin>>>,
    pub is_generating: Arc<Mutex<bool>>,
    pub generating_conv_id: Arc<Mutex<Option<String>>>,
    pub is_loaded: Arc<Mutex<bool>>,
    pub is_engine_ready: Arc<Mutex<bool>>,
    pub active_model: Arc<Mutex<Option<String>>>,
    pub current_device: Arc<Mutex<String>>,
    pub latest_logs: Arc<Mutex<Vec<String>>>,
}

fn find_python_binary(app_dir: &Path) -> String {
    // 1. Explicit env override
    for env_key in ["DARKMAXXER_PYTHON", "PYTHON_PATH"] {
        if let Ok(val) = std::env::var(env_key) {
            let p = PathBuf::from(&val);
            if p.exists() {
                return val;
            }
        }
    }

    // 2. Virtual environments (app_dir, user-local share, /opt, ~/.darkmaxxer, legacy PyEnv)
    let mut path_candidates = vec![
        app_dir.join("venv/bin/python3"),
        app_dir.join("venv/Scripts/python.exe"),
        PathBuf::from("/opt/darkmaxxer/venv/bin/python3"),
    ];

    if let Some(data_dir) = dirs::data_local_dir() {
        path_candidates.push(data_dir.join("darkmaxxer/venv/bin/python3"));
        path_candidates.push(data_dir.join("darkmaxxer/venv/Scripts/python.exe"));
    }
    if let Some(home) = dirs::home_dir() {
        path_candidates.push(home.join(".local/share/darkmaxxer/venv/bin/python3"));
        path_candidates.push(home.join(".darkmaxxer/venv/bin/python3"));
        path_candidates.push(home.join(".darkmaxxer/venv/Scripts/python.exe"));
    }
    #[cfg(not(target_os = "windows"))]
    path_candidates.push(PathBuf::from("/run/media/kairo/S-M-X-F/Da-Ta/PyEnv/bin/python3"));

    if let Some(found) = path_candidates.iter().find(|p| p.exists()) {
        return found.to_string_lossy().to_string();
    }

    // 3. Probe system PATH python executables cleanly
    #[cfg(target_os = "windows")]
    let sys_candidates = ["python", "py", "python3"];
    #[cfg(not(target_os = "windows"))]
    let sys_candidates = ["python3", "python"];

    for cand in sys_candidates {
        let mut probe = Command::new(cand);
        probe.arg("--version");
        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            probe.creation_flags(0x08000000);
        }
        if let Ok(out) = probe.output() {
            let ver = String::from_utf8_lossy(&out.stdout);
            if out.status.success() && ver.contains("Python 3") {
                return cand.to_string();
            }
        }
    }

    #[cfg(target_os = "windows")]
    { "python".to_string() }
    #[cfg(not(target_os = "windows"))]
    { "python3".to_string() }
}

impl EngineSupervisor {
    pub fn new() -> Self {
        Self {
            process: Arc::new(Mutex::new(None)),
            stdin_writer: Arc::new(Mutex::new(None)),
            is_generating: Arc::new(Mutex::new(false)),
            generating_conv_id: Arc::new(Mutex::new(None)),
            is_loaded: Arc::new(Mutex::new(false)),
            is_engine_ready: Arc::new(Mutex::new(false)),
            active_model: Arc::new(Mutex::new(None)),
            current_device: Arc::new(Mutex::new("cpu".to_string())),
            latest_logs: Arc::new(Mutex::new(Vec::new())),
        }
    }

    pub fn start(&self, app_dir: &Path, on_event: Arc<dyn Fn(EngineEvent) + Send + Sync + 'static>) -> Result<(), String> {
        let python_bin = find_python_binary(app_dir);

        // Resolve engine_runner.py script
        let mut script_candidates = vec![app_dir.join("engine_runner.py")];
        if let Some(data_dir) = dirs::data_local_dir() {
            script_candidates.push(data_dir.join("darkmaxxer/engine_runner.py"));
        }
        script_candidates.push(PathBuf::from("/opt/darkmaxxer/engine_runner.py"));

        let script_path = script_candidates.iter()
            .find(|p| p.exists())
            .cloned()
            .ok_or_else(|| "Engine daemon script (engine_runner.py) not found".to_string())?;

        let mut cmd = Command::new(&python_bin);
        cmd.arg(&script_path)
            .current_dir(script_path.parent().unwrap_or(app_dir))
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::inherit());

        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
        }

        let mut child = cmd
            .spawn()
            .map_err(|e| format!("Failed to spawn AI engine daemon ({}): {}", python_bin, e))?;

        let stdin = child.stdin.take().ok_or("Failed to open child stdin")?;
        let stdout = child.stdout.take().ok_or("Failed to open child stdout")?;

        *self.stdin_writer.lock().unwrap() = Some(stdin);
        *self.process.lock().unwrap() = Some(child);

        // Spawn reader thread
        let is_gen_clone = Arc::clone(&self.is_generating);
        let gen_conv_clone = Arc::clone(&self.generating_conv_id);
        let is_loaded_clone = Arc::clone(&self.is_loaded);
        let is_ready_clone = Arc::clone(&self.is_engine_ready);
        let active_model_clone = Arc::clone(&self.active_model);
        let device_clone = Arc::clone(&self.current_device);
        let logs_clone = Arc::clone(&self.latest_logs);

        thread::spawn(move || {
            let reader = BufReader::new(stdout);
            for line in reader.lines().flatten() {
                if let Ok(evt) = serde_json::from_str::<EngineEvent>(&line) {
                    match evt.event.as_str() {
                        "ready" => {
                            *is_ready_clone.lock().unwrap() = true;
                        }
                        "status" => {
                            if let Some(ref m) = evt.message {
                                let mut l = logs_clone.lock().unwrap();
                                l.push(m.clone());
                                if l.len() > 100 {
                                    l.remove(0);
                                }
                            }
                        }
                        "loaded" => {
                            if evt.success == Some(true) {
                                *is_loaded_clone.lock().unwrap() = true;
                                *active_model_clone.lock().unwrap() = evt.model_path.clone();
                                if let Some(ref dev) = evt.device {
                                    *device_clone.lock().unwrap() = dev.clone();
                                }
                            } else {
                                *is_loaded_clone.lock().unwrap() = false;
                                *active_model_clone.lock().unwrap() = None;
                            }
                        }
                        "generation_complete" | "cancelled" | "error" => {
                            *is_gen_clone.lock().unwrap() = false;
                            *gen_conv_clone.lock().unwrap() = None;
                        }
                        _ => {}
                    }
                    on_event(evt);
                }
            }
        });

        Ok(())
    }

    pub fn is_ready(&self) -> bool {
        *self.is_engine_ready.lock().unwrap()
    }

    pub fn send_command(&self, cmd: serde_json::Value) -> Result<(), String> {
        let mut writer_guard = self.stdin_writer.lock().unwrap();
        if let Some(ref mut stdin) = *writer_guard {
            let mut line = serde_json::to_string(&cmd).map_err(|e| e.to_string())?;
            line.push('\n');
            stdin
                .write_all(line.as_bytes())
                .map_err(|e| format!("Failed to send command to engine: {}", e))?;
            stdin.flush().map_err(|e| format!("Failed to flush engine stdin: {}", e))?;
            Ok(())
        } else {
            Err("Engine is not running".to_string())
        }
    }

    pub fn load_model(&self, model_path: &str, use_gpu: bool, compute_mode: Option<&str>) -> Result<(), String> {
        self.send_command(serde_json::json!({
            "action": "load_model",
            "model_path": model_path,
            "use_gpu": use_gpu,
            "compute_mode": compute_mode
        }))
    }

    pub fn generate(&self, prompt: &str, max_new_tokens: usize, temperature: f64) -> Result<(), String> {
        *self.is_generating.lock().unwrap() = true;
        self.send_command(serde_json::json!({
            "action": "generate",
            "prompt": prompt,
            "max_new_tokens": max_new_tokens,
            "temperature": temperature
        }))
    }

    pub fn cancel(&self) -> Result<(), String> {
        self.send_command(serde_json::json!({
            "action": "cancel"
        }))
    }

    pub fn check_compatibility(&self, model_path: &str) -> Result<(), String> {
        self.send_command(serde_json::json!({
            "action": "compatibility_check",
            "model_path": model_path
        }))
    }

    pub fn stop(&self) {
        let _ = self.cancel();
        let mut proc_guard = self.process.lock().unwrap();
        if let Some(mut child) = proc_guard.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
        let mut writer_guard = self.stdin_writer.lock().unwrap();
        *writer_guard = None;
    }
}

impl Drop for EngineSupervisor {
    fn drop(&mut self) {
        self.stop();
    }
}
