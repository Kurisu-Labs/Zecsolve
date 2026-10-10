use gp_core::{
    ensure_transaction_id, ock_from_bytes, parse_transaction, recover_orchard, recover_sapling,
};
use gp_types::{Network, Pool, Receipt};
use serde::Serialize;
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::{fs::File, io::Read, path::Path, process::ExitCode};
use zcash_address::{
    unified::{self, Encoding, Receiver},
    ToAddress, ZcashAddress,
};
use zcash_protocol::consensus::{BranchId, NetworkType};

const REVISION: &str = "f6468e6d08a7adad53bf2991a311358dc84e869b";
const MAX_RECEIPT_BYTES: u64 = 16 * 1024;
const MAX_TX_HEX_BYTES: u64 = 4_000_002;

#[derive(Serialize)]
struct Verifier {
    name: &'static str,
    version: &'static str,
    glasspane_revision: &'static str,
}

#[derive(Serialize)]
struct Output {
    network: Network,
    pool: Pool,
    txid: String,
    output_index: u32,
    amount_zat: u64,
    receiver_hex: String,
    receiver_address: String,
    memo_hex: String,
}

#[derive(Serialize)]
struct Report {
    schema_version: &'static str,
    verifier: Verifier,
    receipt_state: &'static str,
    chain_state: &'static str,
    reason_code: &'static str,
    raw_tx_verified: bool,
    signature_state: &'static str,
    receipt_sha256: Option<String>,
    raw_tx_sha256: Option<String>,
    output: Option<Output>,
}

impl Report {
    fn new() -> Self {
        Self {
            schema_version: "1",
            verifier: Verifier {
                name: "zecsolve-verifier",
                version: env!("CARGO_PKG_VERSION"),
                glasspane_revision: REVISION,
            },
            receipt_state: "ERROR",
            chain_state: "UNAVAILABLE",
            reason_code: "INTERNAL_ERROR",
            raw_tx_verified: false,
            signature_state: "NONE",
            receipt_sha256: None,
            raw_tx_sha256: None,
            output: None,
        }
    }

    fn fail(mut self, state: &'static str, reason: &'static str) -> Self {
        self.receipt_state = state;
        self.reason_code = reason;
        self
    }
}

// Bound actual reads, including files growing after metadata checks.
fn read_bounded(path: &Path, max: u64) -> Result<Vec<u8>, &'static str> {
    let file = File::open(path).map_err(|_| "INPUT_UNAVAILABLE")?;
    let mut bytes = Vec::new();
    file.take(max + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| "INPUT_UNAVAILABLE")?;
    if bytes.len() as u64 > max {
        return Err("INPUT_TOO_LARGE");
    }
    Ok(bytes)
}

fn verify(receipt_path: &Path, tx_path: &Path) -> Report {
    let mut report = Report::new();
    let receipt_bytes = match read_bounded(receipt_path, MAX_RECEIPT_BYTES) {
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
    report.receipt_sha256 = Some(hex::encode(Sha256::digest(&receipt_bytes)));
    let envelope: Value = match serde_json::from_slice(&receipt_bytes) {
        Ok(Value::Object(object)) => Value::Object(object),
        _ => return report.fail("INVALID", "MALFORMED_RECEIPT"),
    };
    for (field, supported, code) in [
        ("version", &["0"][..], "UNSUPPORTED_RECEIPT_VERSION"),
        ("pool", &["orchard", "sapling"][..], "UNSUPPORTED_POOL"),
        ("network", &["mainnet"][..], "UNSUPPORTED_NETWORK"),
    ] {
        if let Some(value) = envelope.get(field).and_then(Value::as_str) {
            if !supported.contains(&value) {
                return report.fail("UNSUPPORTED", code);
            }
        }
    }
    let receipt: Receipt = match serde_json::from_value(envelope) {
        Ok(receipt) => receipt,
        Err(_) => return report.fail("INVALID", "MALFORMED_RECEIPT"),
    };
    if receipt.validate().is_err() {
        return report.fail("INVALID", "MALFORMED_RECEIPT");
    }
    if receipt
        .signature
        .as_ref()
        .is_some_and(|sig| sig.scheme != "ed25519")
    {
        return report.fail("UNSUPPORTED", "UNSUPPORTED_SIGNATURE_SCHEME");
    }
    match receipt.verify_signature_if_present() {
        Ok(true) => report.signature_state = "VALID",
        Ok(false) => {}
        Err(_) => {
            report.signature_state = "INVALID";
            return report.fail("INVALID", "SIGNATURE_INVALID");
        }
    }
    let tx_hex = match read_bounded(tx_path, MAX_TX_HEX_BYTES) {
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
    let raw = match std::str::from_utf8(&tx_hex)
        .ok()
        .and_then(|s| hex::decode(s.trim()).ok())
    {
        Some(raw) => raw,
        None => return report.fail("ERROR", "MALFORMED_RAW_TRANSACTION"),
    };
    report.raw_tx_sha256 = Some(hex::encode(Sha256::digest(&raw)));
    if raw.len() < 12 {
        return report.fail("ERROR", "MALFORMED_RAW_TRANSACTION");
    }
    let version = u32::from_le_bytes(raw[..4].try_into().unwrap());
    if version != 0x8000_0005 {
        return report.fail("UNSUPPORTED", "UNSUPPORTED_TRANSACTION_VERSION");
    }
    let branch = u32::from_le_bytes(raw[8..12].try_into().unwrap());
    if !matches!(
        BranchId::try_from(branch),
        Ok(BranchId::Nu5 | BranchId::Nu6 | BranchId::Nu6_1 | BranchId::Nu6_2)
    ) {
        return report.fail("UNSUPPORTED", "UNSUPPORTED_CONSENSUS_BRANCH");
    }
    let tx = match parse_transaction(&raw) {
        Ok(tx) => tx,
        Err(_) => return report.fail("ERROR", "MALFORMED_RAW_TRANSACTION"),
    };
    let mut serialized = Vec::new();
    if tx.write(&mut serialized).is_err() || serialized != raw {
        return report.fail("ERROR", "NONCANONICAL_RAW_TRANSACTION");
    }
    if ensure_transaction_id(&tx, &receipt.tx_id.to_lowercase()).is_err() {
        return report.fail("INVALID", "TXID_MISMATCH");
    }
    let ock = ock_from_bytes(receipt.ock_bytes().expect("validated above"));
    let recovered = match receipt.pool {
        Pool::Orchard => {
            let action = tx
                .orchard_bundle()
                .and_then(|b| b.actions().iter().nth(receipt.output_index as usize));
            match action {
                None => return report.fail("INVALID", "OUTPUT_NOT_FOUND"),
                Some(action) => recover_orchard(action, &ock)
                    .map(|d| (d.value.inner(), d.recipient.to_raw_address_bytes(), d.memo)),
            }
        }
        Pool::Sapling => {
            let output = tx
                .sapling_bundle()
                .and_then(|b| b.shielded_outputs().get(receipt.output_index as usize));
            match output {
                None => return report.fail("INVALID", "OUTPUT_NOT_FOUND"),
                Some(output) => recover_sapling(
                    output,
                    &ock,
                    sapling_crypto::note_encryption::Zip212Enforcement::On,
                )
                .map(|d| (d.value.inner(), d.recipient.to_bytes(), d.memo)),
            }
        }
    };
    let (amount_zat, receiver_bytes, memo) = match recovered {
        Ok(disclosure) => disclosure,
        Err(_) => return report.fail("INVALID", "OUTPUT_RECOVERY_FAILED"),
    };
    let receiver = match receipt.pool {
        Pool::Orchard => Receiver::Orchard(receiver_bytes),
        Pool::Sapling => Receiver::Sapling(receiver_bytes),
    };
    let address = match unified::Address::try_from_items(vec![receiver]) {
        Ok(address) => ZcashAddress::from_unified(NetworkType::Main, address).encode(),
        Err(_) => return report.fail("ERROR", "ADDRESS_ENCODING_FAILED"),
    };
    report.output = Some(Output {
        network: receipt.network,
        pool: receipt.pool,
        txid: tx.txid().to_string(),
        output_index: receipt.output_index,
        amount_zat,
        receiver_hex: hex::encode(receiver_bytes),
        receiver_address: address,
        memo_hex: hex::encode(memo),
    });
    report.receipt_state = "VALID";
    report.reason_code = "OUTPUT_RECOVERED";
    report.raw_tx_verified = true;
    report
}

fn main() -> ExitCode {
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    if args.len() == 1 && args[0] == "--version" {
        println!(
            "zecsolve-verifier {} glasspane:{}",
            env!("CARGO_PKG_VERSION"),
            REVISION
        );
        return ExitCode::SUCCESS;
    }
    if args.len() != 4 || args[0] != "--receipt" || args[2] != "--raw-tx" {
        eprintln!("Usage: zecsolve-verifier --receipt FILE --raw-tx HEX_FILE");
        return ExitCode::from(64);
    }
    let report = verify(Path::new(&args[1]), Path::new(&args[3]));
    // Domain rejection is a successful invocation; inspect receipt_state.
    println!(
        "{}",
        serde_json::to_string(&report).expect("serializable report")
    );
    ExitCode::SUCCESS
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn historical_mainnet_output_recovers_without_claiming_confirmation() {
        let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
        let report = verify(
            &root.join("fixtures/mainnet/receipt.json"),
            &root.join("fixtures/mainnet/transaction.hex"),
        );
        assert_eq!(report.receipt_state, "VALID");
        assert_eq!(report.chain_state, "UNAVAILABLE");
        let output = report.output.unwrap();
        assert_eq!(output.amount_zat, 100_000);
        assert_eq!(output.output_index, 1);
        assert_eq!(
            output.txid,
            "66167cd3020eb329446e86d80ccd0494baa3959bf9a0e586dbdccd204b6dcfd0"
        );
        assert_eq!(
            hex::decode(output.memo_hex).unwrap()[..23],
            *b"glasspane first receipt"
        );
    }

    #[test]
    fn tampered_ock_cannot_recover_output() {
        let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
        let report = verify(
            &root.join("fixtures/negative/tampered-ock.json"),
            &root.join("fixtures/mainnet/transaction.hex"),
        );
        assert_eq!(report.receipt_state, "INVALID");
        assert_eq!(report.reason_code, "OUTPUT_RECOVERY_FAILED");
        assert!(report.output.is_none());
        assert!(!report.raw_tx_verified);
    }
}
