// [Vikalp Sharma] - Proprietary / Anti-Theft Watermark
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;
use std::process::Command;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileNode {
    pub name: String,
    pub path: String,
    pub is_dir: bool,
    #[serde(default)]
    pub children: Option<Vec<FileNode>>,
}

pub struct FileOps;

impl FileOps {
    pub fn select_model_file() -> Option<String> {
        let file = rfd::FileDialog::new()
            .set_title("Select Model File")
            .add_filter("Model Files", &["gguf", "safetensors", "bin", "pth", "pt", "onnx", "json"])
            .pick_file();
        file.map(|p| p.to_string_lossy().to_string())
    }

    pub fn select_model_folder() -> Option<String> {
        let folder = rfd::FileDialog::new()
            .set_title("Select Model Folder")
            .pick_folder();
        folder.map(|p| p.to_string_lossy().to_string())
    }

    pub fn select_workspace_folder() -> Option<String> {
        let folder = rfd::FileDialog::new()
            .set_title("Select Workspace Directory")
            .pick_folder();
        folder.map(|p| p.to_string_lossy().to_string())
    }

    /// Flatten workspace directory into relative (folders, files) lists using forward slashes.
    pub fn list_flat_tree(root_path: &Path) -> Option<(Vec<String>, Vec<String>)> {
        if !root_path.exists() {
            return None;
        }

        fn walk(root: &Path, current: &Path, depth: usize, folders: &mut Vec<String>, files: &mut Vec<String>) {
            if depth > 5 || (folders.len() + files.len()) > 2000 {
                return;
            }
            if let Ok(entries) = fs::read_dir(current) {
                let mut sorted: Vec<_> = entries.flatten().map(|e| e.path()).collect();
                sorted.sort();
                for p in sorted {
                    let name = p.file_name().unwrap_or_default().to_string_lossy();
                    if name.starts_with('.')
                        || name == "target"
                        || name == "venv"
                        || name == "__pycache__"
                        || name == "node_modules"
                    {
                        continue;
                    }
                    let rel = p.strip_prefix(root).ok()
                        .map(|r| r.to_string_lossy().replace('\\', "/"))
                        .unwrap_or_default();
                    if rel.is_empty() {
                        continue;
                    }
                    if p.is_dir() {
                        folders.push(rel);
                        walk(root, &p, depth + 1, folders, files);
                    } else {
                        files.push(rel);
                    }
                }
            }
        }

        let mut folders = Vec::new();
        let mut files = Vec::new();
        walk(root_path, root_path, 0, &mut folders, &mut files);
        Some((folders, files))
    }

    pub fn get_file_tree(root_path: &Path) -> Option<FileNode> {
        if !root_path.exists() {
            return None;
        }

        fn build_tree(path: &Path, depth: usize) -> Option<FileNode> {
            if depth > 5 {
                return None;
            }
            let name = path.file_name()?.to_string_lossy().to_string();
            let is_dir = path.is_dir();

            let children = if is_dir {
                let mut list = Vec::new();
                if let Ok(entries) = fs::read_dir(path) {
                    for entry in entries.flatten() {
                        let p = entry.path();
                        let sub_name = p.file_name().unwrap_or_default().to_string_lossy();
                        if sub_name.starts_with('.') || sub_name == "target" || sub_name == "__pycache__" || sub_name == "node_modules" {
                            continue;
                        }
                        if let Some(node) = build_tree(&p, depth + 1) {
                            list.push(node);
                        }
                    }
                }
                list.sort_by(|a, b| {
                    if a.is_dir == b.is_dir {
                        a.name.cmp(&b.name)
                    } else if a.is_dir {
                        std::cmp::Ordering::Less
                    } else {
                        std::cmp::Ordering::Greater
                    }
                });
                Some(list)
            } else {
                None
            };

            Some(FileNode {
                name,
                path: path.to_string_lossy().to_string(),
                is_dir,
                children,
            })
        }

        build_tree(root_path, 0)
    }

    pub fn read_file(path: &str) -> Result<String, String> {
        fs::read_to_string(path).map_err(|e| format!("Failed to read file: {}", e))
    }

    pub fn save_file(path: &str, content: &str) -> Result<(), String> {
        let p = Path::new(path);
        if let Some(parent) = p.parent() {
            let _ = fs::create_dir_all(parent);
        }
        fs::write(p, content).map_err(|e| format!("Failed to save file: {}", e))
    }

    pub fn run_command(cmd: &str, cwd: Option<&str>) -> (bool, String) {
        #[cfg(target_os = "windows")]
        let mut process = {
            use std::os::windows::process::CommandExt;
            let mut c = Command::new("cmd");
            c.args(["/C", cmd]);
            c.creation_flags(0x08000000); // CREATE_NO_WINDOW
            c
        };

        #[cfg(not(target_os = "windows"))]
        let mut process = {
            let mut c = Command::new("bash");
            c.args(["-c", cmd]);
            c
        };

        if let Some(dir) = cwd {
            if Path::new(dir).exists() {
                process.current_dir(dir);
            }
        }

        match process.output() {
            Ok(output) => {
                let stdout = String::from_utf8_lossy(&output.stdout).to_string();
                let stderr = String::from_utf8_lossy(&output.stderr).to_string();
                let full = if stderr.is_empty() {
                    stdout
                } else if stdout.is_empty() {
                    stderr
                } else {
                    format!("{}\n{}", stdout, stderr)
                };
                (output.status.success(), full)
            }
            Err(e) => (false, format!("Failed to execute command: {}", e)),
        }
    }
}
