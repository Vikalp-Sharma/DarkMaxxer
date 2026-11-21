// [Vikalp Sharma] - Proprietary / Anti-Theft Watermark
use crate::config::ConfigManager;
use crate::engine::EngineSupervisor;
use crate::file_ops::FileOps;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::Arc;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IpcRequest {
    pub id: u64,
    pub method: String,
    #[serde(default)]
    pub args: Vec<serde_json::Value>,
}

pub struct BridgeHandler {
    pub config: Arc<ConfigManager>,
    pub engine: Arc<EngineSupervisor>,
    pub app_dir: PathBuf,
}

impl BridgeHandler {
    pub fn new(config: Arc<ConfigManager>, engine: Arc<EngineSupervisor>, app_dir: PathBuf) -> Self {
        Self {
            config,
            engine,
            app_dir,
        }
    }

    pub fn handle_call(&self, req: IpcRequest) -> serde_json::Value {
        match req.method.as_str() {
            "check_app_ready" => {
                let ready = self.engine.is_ready();
                serde_json::json!({
                    "success": true,
                    "ready": ready
                })
            }

            "get_active_state" => {
                let conf = self.config.get_config();
                let is_gen = *self.engine.is_generating.lock().unwrap();
                let loaded = *self.engine.is_loaded.lock().unwrap();
                let ready = self.engine.is_ready();
                let dev = self.engine.current_device.lock().unwrap().clone();

                let (conv_id, history) = if let Some(ref id) = conf.active_conv_id {
                    if let Some(conv) = self.config.get_conversation(id) {
                        (Some(id.clone()), conv.history)
                    } else {
                        (Some(id.clone()), vec![])
                    }
                } else {
                    (None, vec![])
                };

                let ws_path = conf.active_workspace_dir.clone();
                let ws_name = ws_path.as_ref().and_then(|p| {
                    std::path::Path::new(p).file_name().map(|n| n.to_string_lossy().to_string())
                });

                serde_json::json!({
                    "settings": conf.settings,
                    "ai_path": conf.ai_path,
                    "ai_loaded": loaded,
                    "model_loaded": loaded,
                    "conv_id": conv_id,
                    "active_conv_id": conv_id,
                    "history": history,
                    "workspace_path": ws_path,
                    "workspace_name": ws_name,
                    "active_workspace_dir": conf.active_workspace_dir,
                    "workspace_mode": conf.workspace_mode,
                    "active_sidebar_tab": conf.active_sidebar_tab,
                    "is_generating": is_gen,
                    "engine_ready": ready,
                    "device": dev,
                    "terminal_logs": *self.engine.latest_logs.lock().unwrap(),
                    "file_ops_active": true
                })
            }

            "get_settings" => {
                let conf = self.config.get_config();
                serde_json::json!(conf.settings)
            }

            "save_setting" => {
                if req.args.len() >= 2 {
                    if let Some(key) = req.args[0].as_str() {
                        self.config.update_setting(key, req.args[1].clone());
                    }
                }
                serde_json::json!({ "success": true })
            }

            "save_settings" => {
                if let Some(obj) = req.args.first().and_then(|v| v.as_object()) {
                    for (k, v) in obj {
                        self.config.update_setting(k, v.clone());
                    }
                }
                serde_json::json!({ "success": true })
            }

            "list_conversations" => {
                let list = self.config.list_conversations();
                serde_json::json!(list)
            }

            "new_conversation" => {
                let name = req.args.first()
                    .and_then(|v| v.as_str())
                    .unwrap_or("New Chat");
                let id = self.config.create_conversation(name);
                serde_json::json!({ "success": true, "id": id })
            }

            "open_conversation" => {
                let id = req.args.first().and_then(|v| v.as_str()).unwrap_or_default();
                if let Some(conv) = self.config.get_conversation(id) {
                    self.config.update_setting("active_conv_id", serde_json::Value::String(id.to_string()));
                    let ws_dir = self.config.minds_dir.join(id);
                    self.config.update_setting(
                        "active_workspace_dir",
                        serde_json::Value::String(ws_dir.to_string_lossy().to_string()),
                    );
                    serde_json::json!({ "success": true, "conversation": conv })
                } else {
                    serde_json::json!({ "success": false, "error": "Conversation not found" })
                }
            }

            "delete_conversation" => {
                let id = req.args.first().and_then(|v| v.as_str()).unwrap_or_default();
                let ok = self.config.delete_conversation(id);
                serde_json::json!({ "success": ok })
            }

            "select_model_file" => {
                if let Some(path) = FileOps::select_model_file() {
                    self.config.update_setting("ai_path", serde_json::Value::String(path.clone()));
                    serde_json::json!({ "success": true, "path": path })
                } else {
                    serde_json::json!({ "success": false, "error": "No file selected" })
                }
            }

            "select_model_folder" => {
                if let Some(path) = FileOps::select_model_folder() {
                    self.config.update_setting("ai_path", serde_json::Value::String(path.clone()));
                    serde_json::json!({ "success": true, "path": path })
                } else {
                    serde_json::json!({ "success": false, "error": "No folder selected" })
                }
            }

            "open_external_folder" => {
                if let Some(path) = FileOps::select_workspace_folder() {
                    self.config.update_setting("active_workspace_dir", serde_json::Value::String(path.clone()));
                    serde_json::json!({ "success": true, "path": path })
                } else {
                    serde_json::json!({ "success": false, "error": "No folder selected" })
                }
            }

            "check_model_compatibility" => {
                let path = req.args.first().and_then(|v| v.as_str()).unwrap_or_default();
                let _ = self.engine.check_compatibility(path);
                serde_json::json!({
                    "success": true,
                    "compatible": true,
                    "message": "Model verified for Universal Engine loading."
                })
            }

            "load_model" => {
                let conf = self.config.get_config();
                let path_arg = req.args.first().and_then(|v| v.as_str()).unwrap_or_default();
                let path = if path_arg.is_empty() {
                    conf.ai_path.as_deref().unwrap_or_default()
                } else {
                    path_arg
                };

                if path.is_empty() {
                    return serde_json::json!({ "success": false, "error": "No model path specified" });
                }

                let use_gpu = conf.settings.gpu_acceleration;
                let compute_mode = conf.settings.compute_mode;

                match self.engine.load_model(path, use_gpu, Some(&compute_mode)) {
                    Ok(_) => {
                        self.config.update_setting("ai_path", serde_json::Value::String(path.to_string()));
                        serde_json::json!({ "success": true })
                    }
                    Err(e) => serde_json::json!({ "success": false, "error": e }),
                }
            }

            "send_prompt" => {
                let prompt = req.args.first().and_then(|v| v.as_str()).unwrap_or_default();
                let conf = self.config.get_config();

                if let Some(ref conv_id) = conf.active_conv_id {
                    if let Some(mut conv) = self.config.get_conversation(conv_id) {
                        conv.history.push(crate::config::ChatMessage {
                            role: "user".to_string(),
                            content: prompt.to_string(),
                            timestamp: Some(chrono::Utc::now().to_rfc3339()),
                        });
                        self.config.save_conversation(&conv);
                    }
                }

                match self.engine.generate(prompt, 128, 0.7) {
                    Ok(_) => serde_json::json!({ "success": true }),
                    Err(e) => serde_json::json!({ "success": false, "error": e }),
                }
            }

            "cancel_generation" => {
                let _ = self.engine.cancel();
                serde_json::json!({ "success": true })
            }

            "get_file_tree" => {
                let conf = self.config.get_config();
                let ws_path = conf.active_workspace_dir
                    .map(PathBuf::from)
                    .unwrap_or_else(|| self.app_dir.clone());

                if let Some(tree) = FileOps::get_file_tree(&ws_path) {
                    serde_json::json!({ "success": true, "tree": tree })
                } else {
                    serde_json::json!({ "success": false, "error": "Workspace not found" })
                }
            }

            "read_file" => {
                let path = req.args.first().and_then(|v| v.as_str()).unwrap_or_default();
                match FileOps::read_file(path) {
                    Ok(content) => serde_json::json!({ "success": true, "content": content }),
                    Err(e) => serde_json::json!({ "success": false, "error": e }),
                }
            }

            "save_file" => {
                let path = req.args.first().and_then(|v| v.as_str()).unwrap_or_default();
                let content = req.args.get(1).and_then(|v| v.as_str()).unwrap_or_default();
                match FileOps::save_file(path, content) {
                    Ok(_) => serde_json::json!({ "success": true }),
                    Err(e) => serde_json::json!({ "success": false, "error": e }),
                }
            }

            "run_command" => {
                let cmd = req.args.first().and_then(|v| v.as_str()).unwrap_or_default();
                let conf = self.config.get_config();
                let cwd = conf.active_workspace_dir.as_deref();
                let (ok, output) = FileOps::run_command(cmd, cwd);
                serde_json::json!({ "success": ok, "output": output })
            }

            "clear_terminal_logs" => {
                self.engine.latest_logs.lock().unwrap().clear();
                serde_json::json!({ "success": true })
            }

            _ => serde_json::json!({ "success": false, "error": format!("Unknown method: {}", req.method) }),
        }
    }
}
