// [Vikalp Sharma] - Proprietary / Anti-Theft Watermark
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppSettings {
    #[serde(default = "default_true")]
    pub local_inference: bool,
    #[serde(default = "default_true")]
    pub gpu_acceleration: bool,
    #[serde(default = "default_compute_mode")]
    pub compute_mode: String,
    #[serde(default = "default_true")]
    pub context_memory: bool,
}

fn default_true() -> bool {
    true
}

fn default_compute_mode() -> String {
    "cpu".to_string()
}

impl Default for AppSettings {
    fn default() -> Self {
        Self {
            local_inference: true,
            gpu_acceleration: true,
            compute_mode: "cpu".to_string(),
            context_memory: true,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    #[serde(default)]
    pub settings: AppSettings,
    pub ai_path: Option<String>,
    pub active_conv_id: Option<String>,
    pub active_workspace_dir: Option<String>,
    #[serde(default = "default_workspace_mode")]
    pub workspace_mode: String,
    #[serde(default = "default_sidebar_tab")]
    pub active_sidebar_tab: String,
}

fn default_workspace_mode() -> String {
    "local".to_string()
}

fn default_sidebar_tab() -> String {
    "chats".to_string()
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            settings: AppSettings::default(),
            ai_path: None,
            active_conv_id: None,
            active_workspace_dir: None,
            workspace_mode: "local".to_string(),
            active_sidebar_tab: "chats".to_string(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: String,
    pub content: String,
    #[serde(default)]
    pub timestamp: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConversationData {
    pub id: String,
    pub name: String,
    #[serde(default)]
    pub history: Vec<ChatMessage>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConversationListItem {
    pub id: String,
    pub name: String,
}

pub struct ConfigManager {
    pub context_dir: PathBuf,
    pub minds_dir: PathBuf,
    pub config_file: PathBuf,
    config: Arc<Mutex<AppConfig>>,
}

impl ConfigManager {
    pub fn new() -> Self {
        let base_dir = dirs::config_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("DarkMaxxer");

        let context_dir = base_dir.join("Context");
        let minds_dir = base_dir.join("Chat");
        let config_file = base_dir.join("config.json");

        let _ = fs::create_dir_all(&context_dir);
        let _ = fs::create_dir_all(&minds_dir);

        // Also check if local config.json exists in working dir
        let local_config = PathBuf::from("config.json");
        let target_config = if local_config.exists() {
            local_config
        } else {
            config_file
        };

        let loaded_config = if target_config.exists() {
            match fs::read_to_string(&target_config) {
                Ok(content) => serde_json::from_str(&content).unwrap_or_default(),
                Err(_) => AppConfig::default(),
            }
        } else {
            AppConfig::default()
        };

        Self {
            context_dir,
            minds_dir,
            config_file: target_config,
            config: Arc::new(Mutex::new(loaded_config)),
        }
    }

    pub fn get_config(&self) -> AppConfig {
        self.config.lock().unwrap().clone()
    }

    pub fn save_config(&self) {
        let conf = self.config.lock().unwrap().clone();
        if let Ok(json) = serde_json::to_string_pretty(&conf) {
            let _ = fs::write(&self.config_file, json);
        }
    }

    pub fn update_setting(&self, key: &str, value: serde_json::Value) {
        let mut conf = self.config.lock().unwrap();
        match key {
            "local_inference" => {
                if let Some(b) = value.as_bool() {
                    conf.settings.local_inference = b;
                }
            }
            "gpu_acceleration" => {
                if let Some(b) = value.as_bool() {
                    conf.settings.gpu_acceleration = b;
                }
            }
            "compute_mode" => {
                if let Some(s) = value.as_str() {
                    conf.settings.compute_mode = s.to_string();
                }
            }
            "context_memory" => {
                if let Some(b) = value.as_bool() {
                    conf.settings.context_memory = b;
                }
            }
            "ai_path" => {
                conf.ai_path = value.as_str().map(|s| s.to_string());
            }
            "active_conv_id" => {
                conf.active_conv_id = value.as_str().map(|s| s.to_string());
            }
            "active_workspace_dir" => {
                conf.active_workspace_dir = value.as_str().map(|s| s.to_string());
            }
            "active_sidebar_tab" => {
                if let Some(s) = value.as_str() {
                    conf.active_sidebar_tab = s.to_string();
                }
            }
            _ => {}
        }
        drop(conf);
        self.save_config();
    }

    pub fn create_conversation(&self, name: &str) -> String {
        let conv_id = Uuid::new_v4().to_string();
        let ws_dir = self.minds_dir.join(&conv_id);
        let _ = fs::create_dir_all(&ws_dir);

        let conv = ConversationData {
            id: conv_id.clone(),
            name: name.to_string(),
            history: Vec::new(),
        };

        let file_path = self.context_dir.join(format!("{}.json", conv_id));
        if let Ok(json) = serde_json::to_string_pretty(&conv) {
            let _ = fs::write(file_path, json);
        }

        self.update_setting("active_conv_id", serde_json::Value::String(conv_id.clone()));
        self.update_setting(
            "active_workspace_dir",
            serde_json::Value::String(ws_dir.to_string_lossy().to_string()),
        );

        conv_id
    }

    pub fn list_conversations(&self) -> Vec<ConversationListItem> {
        let mut list = Vec::new();
        if let Ok(entries) = fs::read_dir(&self.context_dir) {
            for entry in entries.flatten() {
                let path = entry.path();
                if path.extension().and_then(|e| e.to_str()) == Some("json") {
                    if let Ok(content) = fs::read_to_string(&path) {
                        if let Ok(data) = serde_json::from_str::<ConversationData>(&content) {
                            list.push(ConversationListItem {
                                id: data.id,
                                name: data.name,
                            });
                        }
                    }
                }
            }
        }
        list
    }

    pub fn get_conversation(&self, id: &str) -> Option<ConversationData> {
        let file_path = self.context_dir.join(format!("{}.json", id));
        if file_path.exists() {
            if let Ok(content) = fs::read_to_string(file_path) {
                return serde_json::from_str(&content).ok();
            }
        }
        None
    }

    pub fn save_conversation(&self, conv: &ConversationData) {
        let file_path = self.context_dir.join(format!("{}.json", conv.id));
        if let Ok(json) = serde_json::to_string_pretty(conv) {
            let _ = fs::write(file_path, json);
        }
    }

    pub fn delete_conversation(&self, id: &str) -> bool {
        let file_path = self.context_dir.join(format!("{}.json", id));
        let ws_dir = self.minds_dir.join(id);

        let _ = fs::remove_file(file_path);
        let _ = fs::remove_dir_all(ws_dir);

        let mut conf = self.config.lock().unwrap();
        if conf.active_conv_id.as_deref() == Some(id) {
            conf.active_conv_id = None;
            conf.active_workspace_dir = None;
            drop(conf);
            self.save_config();
        }
        true
    }
}
