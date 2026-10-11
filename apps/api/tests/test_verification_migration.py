import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select, text

pytestmark = pytest.mark.postgres


def test_legacy_verification_and_observation_gain_no_invented_context(database, root):
    from zecsolve.db.models import ChainObservation, Verification, VerificationEvaluation

    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "apps/api/migrations"))
    merchant, invoice, case, evidence, verification, observation = [uuid.uuid4() for _ in range(6)]
    with database.begin() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "0005")
        connection.execute(
            text("INSERT INTO merchants(id,name) VALUES (:id,'Legacy')"), {"id": merchant}
        )
        connection.execute(
            text(
                "INSERT INTO invoices(id,merchant_id,network,pool,expected_zat,expected_receiver,"
                "receiver_hex,snapshot_hash,policy_version) "
                "VALUES (:id,:merchant,'mainnet','orchard',1,'legacy',:receiver,:hash,'legacy')"
            ),
            {"id": invoice, "merchant": merchant, "receiver": "00" * 43, "hash": "ab" * 32},
        )
        connection.execute(
            text(
                "INSERT INTO cases(id,invoice_id,merchant_id,state,version) "
                "VALUES (:id,:invoice,:merchant,'OPEN',1)"
            ),
            {"id": case, "invoice": invoice, "merchant": merchant},
        )
        connection.execute(
            text(
                "INSERT INTO evidence(id,case_id,type,source,sha256,storage_ref) "
                "VALUES (:id,:case,'receipt','legacy',:hash,'old')"
            ),
            {"id": evidence, "case": case, "hash": "ab" * 32},
        )
        connection.execute(
            text(
                "INSERT INTO verifications(id,evidence_id,receipt_state,result,"
                "verifier_version,rules_version) "
                "VALUES (:id,:evidence,'NONE','{}','legacy','legacy')"
            ),
            {"id": verification, "evidence": evidence},
        )
        connection.execute(
            text(
                "INSERT INTO chain_observations(id,verification_id,state,source,observed_at) "
                "VALUES (:id,:verification,'UNAVAILABLE','legacy',now())"
            ),
            {"id": observation, "verification": verification},
        )
        command.upgrade(config, "head")
        row = (
            connection.execute(
                select(Verification.__table__).where(Verification.id == verification)
            )
            .mappings()
            .one()
        )
        assert row["result"] == {} and row["workflow_version"] is None and row["case_id"] is None
        assert (
            connection.scalar(
                select(ChainObservation.provenance).where(ChainObservation.id == observation)
            )
            is None
        )
        assert connection.execute(select(VerificationEvaluation)).first() is None
