use serde::Serialize;
use zcash_address::{
    unified::{self, Container, Receiver},
    ConversionError, TryFromAddress, ZcashAddress,
};
use zcash_protocol::consensus::NetworkType;

pub const MAX_ADDRESS_BYTES: usize = 1024;

#[derive(Debug, Serialize)]
pub struct NormalizedReceiver {
    pub network: &'static str,
    pub pool: String,
    pub receiver_hex: String,
}

struct ShieldedReceivers(Vec<Receiver>);

impl TryFromAddress for ShieldedReceivers {
    type Error = &'static str;

    fn try_from_sapling(
        _: NetworkType,
        data: [u8; 43],
    ) -> Result<Self, ConversionError<Self::Error>> {
        Ok(Self(vec![Receiver::Sapling(data)]))
    }

    fn try_from_unified(
        _: NetworkType,
        data: unified::Address,
    ) -> Result<Self, ConversionError<Self::Error>> {
        Ok(Self(data.items()))
    }
}

pub fn normalize(
    address: &str,
    network: &str,
    pool: &str,
) -> Result<NormalizedReceiver, &'static str> {
    if network != "mainnet" {
        return Err("UNSUPPORTED_NETWORK");
    }
    if !matches!(pool, "orchard" | "sapling") {
        return Err("UNSUPPORTED_POOL");
    }
    if address.len() > MAX_ADDRESS_BYTES {
        return Err("INPUT_TOO_LARGE");
    }
    if address.is_empty() || address.trim() != address {
        return Err("INVALID_ADDRESS");
    }
    let address = ZcashAddress::try_from_encoded(address).map_err(|_| "INVALID_ADDRESS")?;
    let receivers = address
        .convert_if_network::<ShieldedReceivers>(NetworkType::Main)
        .map_err(|error| match error {
            ConversionError::IncorrectNetwork { .. } => "NETWORK_MISMATCH",
            _ => "RECEIVER_MISSING",
        })?;
    for receiver in receivers.0 {
        let bytes = match (pool, receiver) {
            ("orchard", Receiver::Orchard(bytes)) => {
                if !bool::from(orchard::Address::from_raw_address_bytes(&bytes).is_some()) {
                    return Err("INVALID_RECEIVER");
                }
                bytes
            }
            ("sapling", Receiver::Sapling(bytes)) => {
                if sapling_crypto::PaymentAddress::from_bytes(&bytes).is_none() {
                    return Err("INVALID_RECEIVER");
                }
                bytes
            }
            _ => continue,
        };
        return Ok(NormalizedReceiver {
            network: "mainnet",
            pool: pool.to_owned(),
            receiver_hex: hex::encode(bytes),
        });
    }
    Err("RECEIVER_MISSING")
}
