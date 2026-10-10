use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::path::Path;
use zecsolve_verifier::address::{normalize, NormalizedReceiver};

const MAX_REQUEST_BYTES: u64 = 8192;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    address: String,
    network: String,
    pool: String,
}

#[derive(Serialize)]
pub struct Report {
    schema_version: &'static str,
    state: &'static str,
    reason_code: &'static str,
    input_sha256: Option<String>,
    receiver: Option<NormalizedReceiver>,
}

impl Report {
    fn fail(mut self, state: &'static str, reason: &'static str) -> Self {
        self.state = state;
        self.reason_code = reason;
        self
    }
}

pub fn run(path: &Path) -> Report {
    let mut report = Report {
        schema_version: "1",
        state: "ERROR",
        reason_code: "INTERNAL_ERROR",
        input_sha256: None,
        receiver: None,
    };
    let bytes = match crate::read_bounded(path, MAX_REQUEST_BYTES) {
        Ok(bytes) => bytes,
        Err(code) => {
            return report.fail(
                if code == "INPUT_UNAVAILABLE" {
                    "UNAVAILABLE"
                } else {
                    "ERROR"
                },
                code,
            )
        }
    };
    report.input_sha256 = Some(hex::encode(Sha256::digest(&bytes)));
    let request: Request = match serde_json::from_slice(&bytes) {
        Ok(request) => request,
        Err(_) => return report.fail("INVALID", "MALFORMED_ADDRESS_REQUEST"),
    };
    match normalize(&request.address, &request.network, &request.pool) {
        Ok(receiver) => {
            report.state = "VALID";
            report.reason_code = "ADDRESS_NORMALIZED";
            report.receiver = Some(receiver);
            report
        }
        Err(code) => report.fail(
            match code {
                "UNSUPPORTED_NETWORK" | "UNSUPPORTED_POOL" => "UNSUPPORTED",
                "INPUT_TOO_LARGE" => "ERROR",
                _ => "INVALID",
            },
            code,
        ),
    }
}
