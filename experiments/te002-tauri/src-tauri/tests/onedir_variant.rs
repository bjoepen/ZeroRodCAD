//! TE-002.1 section 12: proves Variant B (onedir) works when driven from
//! Rust process-control code, not just a shell pipe. Uses plain
//! `std::process::Command` (the same primitive `tauri_plugin_shell` itself
//! wraps) rather than a full Tauri `AppHandle`, since spawning a sidecar via
//! Rust code is not subject to the WebView-facing capability system either
//! way (see src/sidecar.rs's own doc comments). Skipped when the onedir
//! build artifact isn't present (it's a benchmark artifact, not committed).

use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};

fn onedir_binary_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../onedir-dist/zerorod-engine/zerorod-engine")
}

#[test]
fn onedir_sidecar_responds_to_a_real_preview_request_via_std_process_command() {
    let binary = onedir_binary_path();
    if !binary.exists() {
        eprintln!(
            "SKIPPED: onedir build artifact not present at {binary:?} — run \
             PyInstaller against tools/poc/tauri/sidecar-onedir.spec first"
        );
        return;
    }

    let mut child = Command::new(&binary)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("failed to spawn onedir sidecar from Rust");

    let request = r#"{"schema":"zerorod-sidecar/v1","request_id":"rust-onedir-1","command":"preview","parameters":{}}"#;
    child
        .stdin
        .take()
        .unwrap()
        .write_all(format!("{request}\n").as_bytes())
        .expect("failed to write request to onedir sidecar stdin");

    let output = child
        .wait_with_output()
        .expect("onedir sidecar did not exit");
    assert!(
        output.status.success(),
        "onedir sidecar exited with {:?}",
        output.status
    );

    let stdout = String::from_utf8(output.stdout).expect("stdout was not valid UTF-8");
    let lines: Vec<&str> = stdout.lines().filter(|l| !l.trim().is_empty()).collect();
    assert_eq!(
        lines.len(),
        1,
        "expected exactly one JSON line, got: {stdout:?}"
    );

    let response: serde_json::Value =
        serde_json::from_str(lines[0]).expect("response was not valid JSON");
    assert_eq!(response["schema"], "zerorod-sidecar/v1");
    assert_eq!(response["request_id"], "rust-onedir-1");
    assert_eq!(response["ok"], true);
    assert_eq!(response["result"]["schema"], "zerorod-mesh/v1");
    assert!(!response["result"]["meshes"].as_array().unwrap().is_empty());
}

#[test]
fn onedir_sidecar_supports_persistent_mode_via_std_process_command() {
    let binary = onedir_binary_path();
    if !binary.exists() {
        eprintln!("SKIPPED: onedir build artifact not present at {binary:?}");
        return;
    }

    let mut child = Command::new(&binary)
        .arg("--persistent")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("failed to spawn onedir sidecar in persistent mode from Rust");

    let mut stdin = child.stdin.take().unwrap();
    stdin
        .write_all(b"{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"a\",\"command\":\"ping\",\"parameters\":{}}\n")
        .unwrap();
    stdin
        .write_all(b"{\"schema\":\"zerorod-sidecar/v1\",\"request_id\":\"b\",\"command\":\"shutdown\",\"parameters\":{}}\n")
        .unwrap();
    drop(stdin);

    let output = child
        .wait_with_output()
        .expect("onedir sidecar did not exit");
    assert!(output.status.success());

    let stdout = String::from_utf8(output.stdout).unwrap();
    let lines: Vec<&str> = stdout.lines().filter(|l| !l.trim().is_empty()).collect();
    assert_eq!(
        lines.len(),
        2,
        "expected exactly two JSON lines, got: {stdout:?}"
    );
}
