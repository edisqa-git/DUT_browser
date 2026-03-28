#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use anyhow::{Context, Result};
use std::fs;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::{AppHandle, Manager, RunEvent, State};

const BACKEND_HOST: &str = "127.0.0.1";
const BACKEND_PORT: &str = "8765";

#[derive(Default)]
struct BackendState {
    child: Mutex<Option<Child>>,
}

struct RuntimePaths {
    runtime_root: PathBuf,
    backend_workdir: PathBuf,
    backend_executable: Option<PathBuf>,
    data_root: PathBuf,
}

fn main() {
    let builder = tauri::Builder::default()
        .manage(BackendState::default())
        .setup(|app| {
            let runtime_paths = resolve_runtime_paths(app.handle())?;
            fs::create_dir_all(runtime_paths.data_root.join("logs"))
                .context("failed to create application log directory")?;

            let child = spawn_backend(&runtime_paths)?;
            let state: State<'_, BackendState> = app.state();
            *state.child.lock().expect("backend state poisoned") = Some(child);
            Ok(())
        });

    let app = builder.build(tauri::generate_context!()).expect("failed to build Tauri app");
    app.run(|app_handle, event| {
        if matches!(event, RunEvent::ExitRequested { .. } | RunEvent::Exit) {
            let state: State<'_, BackendState> = app_handle.state();
            stop_backend(&state);
        }
    });
}

fn resolve_runtime_paths(app: AppHandle) -> Result<RuntimePaths> {
    if cfg!(debug_assertions) {
        let repo_root = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../..")
            .canonicalize()
            .context("failed to resolve repository root")?;

        return Ok(RuntimePaths {
            runtime_root: repo_root.clone(),
            backend_workdir: repo_root.join("dut-dashboard/backend"),
            backend_executable: None,
            data_root: repo_root.join("dut-dashboard"),
        });
    }

    let resource_dir = app
        .path_resolver()
        .resource_dir()
        .context("missing Tauri resource directory")?;
    let runtime_root = resource_dir.join("runtime");
    let backend_executable = runtime_root.join("backend").join(if cfg!(target_os = "windows") {
        "dut-backend.exe"
    } else {
        "dut-backend"
    });

    let data_root = app
        .path_resolver()
        .app_local_data_dir()
        .or_else(|| app.path_resolver().app_data_dir())
        .unwrap_or_else(|| runtime_root.join("data"));

    Ok(RuntimePaths {
        runtime_root,
        backend_workdir: resource_dir,
        backend_executable: Some(backend_executable),
        data_root,
    })
}

fn spawn_backend(paths: &RuntimePaths) -> Result<Child> {
    let mut command = if cfg!(debug_assertions) {
        let python = if cfg!(target_os = "windows") { "python" } else { "python3" };
        let mut command = Command::new(python);
        command
            .arg("-m")
            .arg("app.main")
            .arg("--host")
            .arg(BACKEND_HOST)
            .arg("--port")
            .arg(BACKEND_PORT);
        command.current_dir(&paths.backend_workdir);
        command
    } else {
        let backend_executable = paths
            .backend_executable
            .as_ref()
            .context("missing packaged backend executable path")?;
        let mut command = Command::new(backend_executable);
        command
            .arg("--host")
            .arg(BACKEND_HOST)
            .arg("--port")
            .arg(BACKEND_PORT);
        command.current_dir(&paths.backend_workdir);
        command
    };

    command
        .env("DUT_BROWSER_ROOT", &paths.runtime_root)
        .env("DUT_BROWSER_DATA_DIR", &paths.data_root);

    if cfg!(debug_assertions) {
        command.stdout(Stdio::inherit()).stderr(Stdio::inherit());
    } else {
        command.stdout(Stdio::null()).stderr(Stdio::null());
    }

    command.spawn().context("failed to launch DUT backend")
}

fn stop_backend(state: &State<'_, BackendState>) {
    if let Some(mut child) = state.child.lock().expect("backend state poisoned").take() {
        let _ = child.kill();
        let _ = child.wait();
    }
}
