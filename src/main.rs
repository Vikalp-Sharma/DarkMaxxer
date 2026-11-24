// [Vikalp Sharma] - Proprietary / Anti-Theft Watermark
mod bridge;
mod config;
mod engine;
mod file_ops;

use bridge::{BridgeHandler, IpcRequest};
use config::ConfigManager;
use engine::{EngineEvent, EngineSupervisor};
use std::path::PathBuf;
use std::sync::Arc;
use tao::dpi::LogicalSize;
use tao::event::{Event, WindowEvent};
use tao::event_loop::{ControlFlow, EventLoopBuilder};
use tao::window::WindowBuilder;
use wry::WebViewBuilder;
#[cfg(target_os = "linux")]
use tao::platform::unix::WindowExtUnix;
#[cfg(target_os = "linux")]
use wry::WebViewBuilderExtUnix;

enum UserEvent {
    IpcMessage(String),
    EngineUpdate(EngineEvent),
}

fn resolve_app_dir() -> PathBuf {
    // 1. Current working directory if gui/index.html exists
    if let Ok(cwd) = std::env::current_dir() {
        if cwd.join("gui/index.html").exists() {
            return cwd;
        }
    }
    // 2. Binary parent directory if gui/index.html exists
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            if parent.join("gui/index.html").exists() {
                return parent.to_path_buf();
            }
        }
    }
    // 3. System installed directory /opt/darkmaxxer
    let opt_dir = PathBuf::from("/opt/darkmaxxer");
    if opt_dir.join("gui/index.html").exists() {
        return opt_dir;
    }
    PathBuf::from(".")
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("Starting DarkMaxxer 2.0 (Native Rust Core)...");

    let app_dir = resolve_app_dir();
    let index_html = app_dir.join("gui/index.html");

    if !index_html.exists() {
        eprintln!("Error: gui/index.html not found in {:?}", app_dir);
        std::process::exit(1);
    }

    println!("Loaded assets from: {:?}", app_dir);

    let config_mgr = Arc::new(ConfigManager::new());
    let engine_sup = Arc::new(EngineSupervisor::new());
    let bridge = Arc::new(BridgeHandler::new(
        Arc::clone(&config_mgr),
        Arc::clone(&engine_sup),
        app_dir.clone(),
    ));

    // Initialize Event Loop with custom UserEvent
    let event_loop = EventLoopBuilder::<UserEvent>::with_user_event().build();
    let proxy = event_loop.create_proxy();

    // Start engine daemon with event forwarder to GUI
    let proxy_for_engine = proxy.clone();
    let _ = engine_sup.start(
        &app_dir,
        Arc::new(move |evt: EngineEvent| {
            let _ = proxy_for_engine.send_event(UserEvent::EngineUpdate(evt));
        }),
    );

    // Build Tao Native Window
    let window = WindowBuilder::new()
        .with_title("DarkMaxxer AI — Autonomous Intelligence")
        .with_inner_size(LogicalSize::new(1380.0, 880.0))
        .with_min_inner_size(LogicalSize::new(960.0, 600.0))
        .build(&event_loop)?;

    // JavaScript initialization script injected before index.html scripts execute
    let init_script = r#"
        window.pywebview = {
            _callbacks: {},
            _callId: 0,
            api: new Proxy({}, {
                get: function(target, prop) {
                    return function(...args) {
                        return new Promise((resolve, reject) => {
                            const id = ++window.pywebview._callId;
                            window.pywebview._callbacks[id] = { resolve, reject };
                            window.ipc.postMessage(JSON.stringify({ id, method: prop, args }));
                        });
                    };
                }
            })
        };

        window.__darkmaxxer_resolve = function(id, result) {
            if (window.pywebview && window.pywebview._callbacks && window.pywebview._callbacks[id]) {
                window.pywebview._callbacks[id].resolve(result);
                delete window.pywebview._callbacks[id];
            }
        };

        window.__darkmaxxer_reject = function(id, err) {
            if (window.pywebview && window.pywebview._callbacks && window.pywebview._callbacks[id]) {
                window.pywebview._callbacks[id].reject(err);
                delete window.pywebview._callbacks[id];
            }
        };

        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(() => {
                window.dispatchEvent(new Event('pywebviewready'));
            }, 50);
        });
    "#;

    // Build Wry WebView with custom protocol
    let proxy_for_ipc = proxy.clone();
    let gui_dir = app_dir.join("gui");

    let builder = WebViewBuilder::new()
        .with_initialization_script(init_script)
        .with_custom_protocol("darkmaxxer".into(), move |_id, request| {
            let path = request.uri().path();
            let clean_path = path.trim_start_matches('/');
            let target_file = if clean_path.is_empty() || clean_path == "index.html" {
                gui_dir.join("index.html")
            } else {
                gui_dir.join(clean_path)
            };

            if let Ok(data) = std::fs::read(&target_file) {
                let mime = match target_file.extension().and_then(|s| s.to_str()).unwrap_or("") {
                    "html" | "htm" => "text/html; charset=utf-8",
                    "css" => "text/css; charset=utf-8",
                    "js" | "mjs" => "application/javascript; charset=utf-8",
                    "json" => "application/json; charset=utf-8",
                    "png" => "image/png",
                    "jpg" | "jpeg" => "image/jpeg",
                    "gif" => "image/gif",
                    "svg" => "image/svg+xml",
                    "ico" => "image/x-icon",
                    "woff" => "font/woff",
                    "woff2" => "font/woff2",
                    "ttf" => "font/ttf",
                    _ => "application/octet-stream",
                };

                wry::http::Response::builder()
                    .header(wry::http::header::CONTENT_TYPE, mime)
                    .header("Access-Control-Allow-Origin", "*")
                    .status(wry::http::StatusCode::OK)
                    .body(std::borrow::Cow::Owned(data))
                    .unwrap()
            } else {
                wry::http::Response::builder()
                    .status(wry::http::StatusCode::NOT_FOUND)
                    .body(std::borrow::Cow::Borrowed(&b"404 Not Found"[..]))
                    .unwrap()
            }
        })
        .with_background_color((10, 10, 15, 255))
        .with_url("darkmaxxer://localhost/splash.html")
        .with_ipc_handler(move |req: wry::http::Request<String>| {
            let body = req.body().clone();
            let _ = proxy_for_ipc.send_event(UserEvent::IpcMessage(body));
        });

    #[cfg(not(target_os = "linux"))]
    let webview = builder.build(&window)?;

    #[cfg(target_os = "linux")]
    let webview = {
        let vbox = window.default_vbox().expect("Failed to get default vbox from tao window");
        builder.build_gtk(vbox)?
    };

    // Event Loop Runner
    event_loop.run(move |event, _, control_flow| {
        *control_flow = ControlFlow::Wait;

        match event {
            Event::WindowEvent {
                event: WindowEvent::CloseRequested,
                ..
            } => {
                bridge.engine.stop();
                *control_flow = ControlFlow::Exit;
            }

            Event::UserEvent(UserEvent::IpcMessage(raw_msg)) => {
                if let Ok(req) = serde_json::from_str::<IpcRequest>(&raw_msg) {
                    let req_id = req.id;
                    let bridge_clone = Arc::clone(&bridge);
                    let res = bridge_clone.handle_call(req);

                    if let Ok(json_res) = serde_json::to_string(&res) {
                        let eval_js = format!("window.__darkmaxxer_resolve({}, {});", req_id, json_res);
                        let _ = webview.evaluate_script(&eval_js);
                    }
                }
            }

            Event::UserEvent(UserEvent::EngineUpdate(evt)) => {
                match evt.event.as_str() {
                    "status" => {
                        if let Some(ref m) = evt.message {
                            if let Ok(safe_msg) = serde_json::to_string(m) {
                                let js = format!("if(window.updateLoadStatus) window.updateLoadStatus({});", safe_msg);
                                let _ = webview.evaluate_script(&js);
                            }
                        }
                    }
                    "token" => {
                        if let Some(ref t) = evt.token {
                            if let Ok(safe_t) = serde_json::to_string(t) {
                                let js = format!("if(window.renderStreamedToken) window.renderStreamedToken({});", safe_t);
                                let _ = webview.evaluate_script(&js);
                            }
                        }
                    }
                    "loaded" => {
                        let success = evt.success.unwrap_or(false);
                        let dev = evt.device.clone().unwrap_or_else(|| "CPU".to_string());
                        if success {
                            let msg = format!("Model loaded successfully on {}!", dev);
                            if let Ok(safe_msg) = serde_json::to_string(&msg) {
                                let js = format!(
                                    "if(window.updateLoadStatus) window.updateLoadStatus({}, 100); if(window.onModelLoadedSuccess) window.onModelLoadedSuccess();",
                                    safe_msg
                                );
                                let _ = webview.evaluate_script(&js);
                            }
                        } else {
                            let err_msg = evt.error.clone().unwrap_or_else(|| "Failed to load model".to_string());
                            if let Ok(safe_err) = serde_json::to_string(&err_msg) {
                                let js = format!(
                                    "if(window.onModelLoadedError) window.onModelLoadedError({});",
                                    safe_err
                                );
                                let _ = webview.evaluate_script(&js);
                            }
                        }
                    }

                    "generation_complete" => {
                        if let Some(ref txt) = evt.text {
                            // Persist assistant message to active conversation
                            let conf = bridge.config.get_config();
                            if let Some(ref conv_id) = conf.active_conv_id {
                                if let Some(mut conv) = bridge.config.get_conversation(conv_id) {
                                    conv.history.push(crate::config::ChatMessage {
                                        role: "assistant".to_string(),
                                        content: txt.clone(),
                                        timestamp: Some(chrono::Utc::now().to_rfc3339()),
                                    });
                                    bridge.config.save_conversation(&conv);
                                }
                            }

                            if let Ok(safe_txt) = serde_json::to_string(txt) {
                                let js = format!(
                                    "if(window.onGenerationComplete) window.onGenerationComplete({}); if(window.restoreState) window.restoreState();",
                                    safe_txt
                                );
                                let _ = webview.evaluate_script(&js);
                            }
                        }
                    }
                    "cancelled" => {
                        let js = "if(window.restoreState) window.restoreState();";
                        let _ = webview.evaluate_script(js);
                    }
                    "error" => {
                        if let Some(ref m) = evt.message {
                            if let Ok(safe_m) = serde_json::to_string(m) {
                                let js = format!("if(window.appendTerminal) window.appendTerminal('Engine Error: ' + {}); if(window.restoreState) window.restoreState();", safe_m);
                                let _ = webview.evaluate_script(&js);
                            }
                        }
                    }
                    _ => {}
                }
            }

            _ => {}
        }
    });
}
