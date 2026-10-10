use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{
    path::PathBuf,
    process::Command,
    sync::atomic::{AtomicU64, Ordering},
};

struct TestDir(PathBuf);

impl TestDir {
    fn new() -> Self {
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let path = std::env::temp_dir().join(format!(
            "zecsolve-cli-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        std::fs::create_dir(&path).unwrap();
        Self(path)
    }
}

impl Drop for TestDir {
    fn drop(&mut self) {
        std::fs::remove_dir_all(&self.0).unwrap();
    }
}

fn invoke(bytes: &[u8]) -> Value {
    let dir = TestDir::new();
    let input = dir.0.join("request.json");
    std::fs::write(&input, bytes).unwrap();
    let output = Command::new(env!("CARGO_BIN_EXE_zecsolve-verifier"))
        .args(["normalize-address", "--input"])
        .arg(input)
        .output()
        .unwrap();
    assert!(output.status.success(), "{:?}", output);
    assert!(output.stderr.is_empty());
    serde_json::from_slice(&output.stdout).unwrap()
}

#[test]
fn normalizes_historical_address_and_binds_exact_input_bytes() {
    let manifest: Value =
        serde_json::from_str(include_str!("../../../fixtures/manifest.json")).unwrap();
    let input = serde_json::to_vec(&json!({
        "address": manifest["expected"]["receiver_address"],
        "network": "mainnet", "pool": "orchard"
    }))
    .unwrap();
    let report = invoke(&input);
    assert_eq!(report["schema_version"], "1");
    assert_eq!(report["state"], "VALID");
    assert_eq!(report["reason_code"], "ADDRESS_NORMALIZED");
    assert_eq!(report["input_sha256"], hex::encode(Sha256::digest(&input)));
    assert_eq!(report["receiver"]["network"], "mainnet");
    assert_eq!(report["receiver"]["pool"], "orchard");
    assert_eq!(
        report["receiver"]["receiver_hex"],
        "ab7196fa80c61c65508be3923dbb8b416fc9fc50516e33e7be761e5da01b35a857f1770483a36b0f2b07ad"
    );
}

#[test]
fn rejects_invalid_requests_with_machine_readable_results() {
    for input in [
        b"{}".to_vec(),
        b"not json".to_vec(),
        vec![255],
        serde_json::to_vec(&json!({
            "address": "a", "network": "mainnet", "pool": "orchard", "receiver_hex": "untrusted"
        }))
        .unwrap(),
    ] {
        let report = invoke(&input);
        assert_eq!(report["state"], "INVALID");
        assert_eq!(report["reason_code"], "MALFORMED_ADDRESS_REQUEST");
        assert!(report["receiver"].is_null());
    }
    let report = invoke(&vec![b' '; 8193]);
    assert_eq!(report["state"], "ERROR");
    assert_eq!(report["reason_code"], "INPUT_TOO_LARGE");
}

#[test]
fn separates_unsupported_scope_from_invalid_address() {
    for (network, pool, state, reason) in [
        ("mainnet", "orchard", "INVALID", "INVALID_ADDRESS"),
        ("testnet", "orchard", "UNSUPPORTED", "UNSUPPORTED_NETWORK"),
        ("mainnet", "transparent", "UNSUPPORTED", "UNSUPPORTED_POOL"),
    ] {
        let input =
            serde_json::to_vec(&json!({"address":"not an address", "network":network,"pool":pool}))
                .unwrap();
        let report = invoke(&input);
        assert_eq!(report["state"], state);
        assert_eq!(report["reason_code"], reason);
        assert!(report["receiver"].is_null());
    }
}

#[test]
fn missing_input_is_unavailable_and_bad_cli_usage_exits_64() {
    let dir = TestDir::new();
    let output = Command::new(env!("CARGO_BIN_EXE_zecsolve-verifier"))
        .args(["normalize-address", "--input"])
        .arg(dir.0.join("absent.json"))
        .output()
        .unwrap();
    assert!(output.status.success());
    let report: Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(report["state"], "UNAVAILABLE");
    assert_eq!(report["reason_code"], "INPUT_UNAVAILABLE");
    let output = Command::new(env!("CARGO_BIN_EXE_zecsolve-verifier"))
        .arg("normalize-address")
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(64));
    assert!(output.stdout.is_empty());
}
