import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import insert, select, text
from sqlalchemy.exc import IntegrityError
from zecsolve.db.models import Case, Evidence, Invoice, Merchant

pytestmark = pytest.mark.postgres


def seed(connection):
    merchant, invoice, case = [uuid.uuid4() for _ in range(3)]
    connection.execute(insert(Merchant).values(id=merchant, name="Evidence migration"))
    connection.execute(
        insert(Invoice).values(
            id=invoice,
            merchant_id=merchant,
            network="mainnet",
            pool="orchard",
            expected_zat=1,
            expected_receiver="legacy",
            receiver_hex="00" * 43,
            snapshot_hash="ab" * 32,
            policy_version="legacy",
        )
    )
    connection.execute(
        insert(Case).values(
            id=case, merchant_id=merchant, invoice_id=invoice, state="OPEN", version=1
        )
    )
    return merchant, case


def test_existing_evidence_is_preserved_without_claiming_encryption(database, root):
    from zecsolve.db.models import EvidenceContent

    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "apps/api/migrations"))
    with database.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "0004")
        merchant, case = seed(connection)
        identity = uuid.uuid4()
        connection.execute(
            text(
                "INSERT INTO evidence(id,case_id,type,source,sha256,storage_ref) "
                "VALUES (:id,:case,'receipt','legacy',:hash,'old-ref')"
            ),
            {"id": identity, "case": case, "hash": "ab" * 32},
        )
        command.upgrade(config, "head")
        row = (
            connection.execute(select(Evidence.__table__).where(Evidence.id == identity))
            .mappings()
            .one()
        )
        assert row["sha256"] == "ab" * 32 and row["storage_ref"] == "old-ref"
        assert row["bundle_version"] is None and row["bundle_metadata"] is None
        assert connection.execute(select(EvidenceContent)).first() is None


def test_key_nonce_uniqueness_is_enforced(database):
    from zecsolve.db.models import EvidenceContent

    with database.begin() as connection:
        merchant, case = seed(connection)
        ids = [uuid.uuid4(), uuid.uuid4()]
        for identity in ids:
            connection.execute(
                insert(Evidence).values(
                    id=identity,
                    case_id=case,
                    type="encrypted_bundle",
                    source="test",
                    sha256="ab" * 32,
                    storage_ref=str(identity),
                    merchant_id=merchant,
                    bundle_version="1",
                )
            )
        connection.execute(
            insert(EvidenceContent).values(
                evidence_id=ids[0], key_id="test", nonce=bytes(12), ciphertext=bytes(16)
            )
        )
    with pytest.raises(IntegrityError):
        with database.begin() as connection:
            connection.execute(
                insert(EvidenceContent).values(
                    evidence_id=ids[1], key_id="test", nonce=bytes(12), ciphertext=bytes(16)
                )
            )
