use orchard::keys::{FullViewingKey, Scope, SpendingKey};
use sapling_crypto::zip32::ExtendedSpendingKey;
use zcash_address::{
    unified::{self, Encoding, Receiver},
    ToAddress, ZcashAddress,
};
use zcash_protocol::consensus::NetworkType;
use zecsolve_verifier::address::normalize;

fn receivers() -> ([u8; 43], [u8; 43]) {
    // Synthetic address inputs, not additional historical payment fixtures.
    let key = SpendingKey::from_bytes([7; 32]).unwrap();
    let orchard = FullViewingKey::from(&key)
        .address_at(0u32, Scope::External)
        .to_raw_address_bytes();
    let sapling = ExtendedSpendingKey::master(&[7; 32])
        .default_address()
        .1
        .to_bytes();
    (orchard, sapling)
}

fn unified(network: NetworkType, receivers: Vec<Receiver>) -> String {
    ZcashAddress::from_unified(
        network,
        unified::Address::try_from_items(receivers).unwrap(),
    )
    .encode()
}

#[test]
fn selects_requested_receiver_from_mixed_unified_address() {
    let (orchard, sapling) = receivers();
    let address = unified(
        NetworkType::Main,
        vec![
            Receiver::Orchard(orchard),
            Receiver::Sapling(sapling),
            Receiver::P2pkh([1; 20]),
        ],
    );
    for (pool, bytes) in [("orchard", orchard), ("sapling", sapling)] {
        let receiver = normalize(&address, "mainnet", pool).unwrap();
        assert_eq!(receiver.receiver_hex, hex::encode(bytes));
        assert_eq!(receiver.network, "mainnet");
        assert_eq!(receiver.pool, pool);
    }
}

#[test]
fn standalone_and_unified_sapling_have_the_same_identity() {
    let (_, sapling) = receivers();
    let standalone = ZcashAddress::from_sapling(NetworkType::Main, sapling).encode();
    let ua = unified(NetworkType::Main, vec![Receiver::Sapling(sapling)]);
    for address in [&standalone, &ua] {
        assert_eq!(
            normalize(address, "mainnet", "sapling")
                .unwrap()
                .receiver_hex,
            hex::encode(sapling)
        );
        assert_eq!(
            normalize(address, "mainnet", "orchard").unwrap_err(),
            "RECEIVER_MISSING"
        );
    }
}

#[test]
fn rejects_wrong_network_without_changing_receiver_identity() {
    let (orchard, sapling) = receivers();
    for network in [NetworkType::Test, NetworkType::Regtest] {
        for address in [
            unified(network, vec![Receiver::Orchard(orchard)]),
            ZcashAddress::from_sapling(network, sapling).encode(),
        ] {
            assert_eq!(
                normalize(&address, "mainnet", "sapling").unwrap_err(),
                "NETWORK_MISMATCH"
            );
        }
    }
}

#[test]
fn rejects_bad_encoding_unsupported_requests_and_missing_receivers() {
    for address in ["", "not an address", "u1invalid", " zs1invalid "] {
        assert_eq!(
            normalize(address, "mainnet", "orchard").unwrap_err(),
            "INVALID_ADDRESS"
        );
    }
    assert_eq!(
        normalize(&"x".repeat(1025), "mainnet", "orchard").unwrap_err(),
        "INPUT_TOO_LARGE"
    );
    assert_eq!(
        normalize("anything", "testnet", "orchard").unwrap_err(),
        "UNSUPPORTED_NETWORK"
    );
    assert_eq!(
        normalize("anything", "mainnet", "transparent").unwrap_err(),
        "UNSUPPORTED_POOL"
    );
    let transparent = ZcashAddress::from_transparent_p2pkh(NetworkType::Main, [1; 20]).encode();
    assert_eq!(
        normalize(&transparent, "mainnet", "orchard").unwrap_err(),
        "RECEIVER_MISSING"
    );
}

#[test]
fn rejects_invalid_inner_receiver_even_with_valid_outer_checksum() {
    for (pool, receiver) in [
        ("orchard", Receiver::Orchard([255; 43])),
        ("sapling", Receiver::Sapling([255; 43])),
    ] {
        let address = unified(NetworkType::Main, vec![receiver]);
        assert_eq!(
            normalize(&address, "mainnet", pool).unwrap_err(),
            "INVALID_RECEIVER"
        );
    }
    let standalone = ZcashAddress::from_sapling(NetworkType::Main, [255; 43]).encode();
    assert_eq!(
        normalize(&standalone, "mainnet", "sapling").unwrap_err(),
        "INVALID_RECEIVER"
    );
}

#[test]
fn rejects_altered_checksum_and_whitespace_in_a_valid_address() {
    let (orchard, _) = receivers();
    let address = unified(NetworkType::Main, vec![Receiver::Orchard(orchard)]);
    let mut altered = address.clone();
    let last = altered.pop().unwrap();
    altered.push(if last == 'q' { 'p' } else { 'q' });
    for input in [altered, format!(" {address}"), format!("{address}\n")] {
        assert_eq!(
            normalize(&input, "mainnet", "orchard").unwrap_err(),
            "INVALID_ADDRESS"
        );
    }
}
