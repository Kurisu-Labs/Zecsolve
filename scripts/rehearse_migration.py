"""Forward-only 0008 -> packaged head rehearsal in a private disposable schema."""

import base64
import os
import uuid
from datetime import UTC, datetime

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from pydantic import SecretStr
from sqlalchemy import MetaData, Table, select, text
from zecsolve.adapters.evidence_crypto import EvidenceCipher


def rehearse(engine, root):
    schema = "zecsolve_recovery_" + uuid.uuid4().hex
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "apps/api/migrations"))
    head = ScriptDirectory.from_config(config).get_current_head()
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        with engine.begin() as connection:
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            config.attributes["connection"] = connection
            command.upgrade(config, "0008")
            tables = {}

            def insert(table_name, **values):
                table = tables.setdefault(
                    table_name, Table(table_name, MetaData(), autoload_with=connection)
                )
                connection.execute(table.insert().values(**values))

            merchant, invoice, case, evidence, verification, resolution, claim = (
                uuid.uuid4() for _ in range(7)
            )
            insert("merchants", id=merchant, name="Synthetic migration rehearsal")
            insert(
                "invoices",
                id=invoice,
                merchant_id=merchant,
                network="mainnet",
                pool="orchard",
                expected_zat=200_000,
                expected_receiver="synthetic",
                receiver_hex="00" * 43,
                snapshot_hash="ab" * 32,
                policy_version="legacy-rehearsal",
            )
            insert(
                "cases", id=case, invoice_id=invoice, merchant_id=merchant, state="OPEN", version=1
            )
            insert(
                "claims",
                id=claim,
                case_id=case,
                claimant_role="customer",
                note="Synthetic legacy claim",
            )
            cipher = EvidenceCipher(
                "rehearsal", SecretStr(base64.b64encode(os.urandom(32)).decode())
            )
            context = dict(merchant_id=merchant, case_id=case, evidence_id=evidence)
            plaintext = b"Synthetic legacy encrypted bytes\n"
            sealed = cipher.encrypt(plaintext, **context)
            insert(
                "evidence",
                id=evidence,
                case_id=case,
                merchant_id=merchant,
                type="encrypted_bundle",
                source="synthetic-rehearsal",
                sha256="ab" * 32,
                storage_ref="rehearsal-only",
            )
            insert(
                "evidence_contents",
                evidence_id=evidence,
                key_id=sealed.key_id,
                nonce=sealed.nonce,
                ciphertext=sealed.ciphertext,
            )
            insert(
                "verifications",
                id=verification,
                evidence_id=evidence,
                receipt_state="VALID",
                result={},
                verifier_version="synthetic",
                rules_version="legacy",
            )
            insert(
                "resolutions",
                id=resolution,
                case_id=case,
                outcome="PARTIAL_CREDIT",
                reason="Synthetic legacy accounting",
                approved_by="rehearsal",
                approved_at=datetime.now(UTC),
            )
            insert(
                "output_allocations",
                network="mainnet",
                pool="orchard",
                txid="ab" * 32,
                output_index=1,
                invoice_id=invoice,
                verification_id=verification,
                resolution_id=resolution,
                amount_zat=100_000,
            )
            before = {
                name: connection.execute(select(table)).all() for name, table in tables.items()
            }
            command.upgrade(config, "head")
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == head
            assert before == {
                name: connection.execute(select(table)).all() for name, table in tables.items()
            }
            assert cipher.decrypt(sealed, **context) == plaintext
            # New nullable attribution must not invent an owner for historical records.
            assert connection.execute(
                text("SELECT actor_grant_id, actor_credential_id FROM claims")
            ).one() == (None, None)
            assert connection.scalar(text("SELECT count(*) FROM access_submission_requests")) == 0
            # Re-running forward startup migrations must also preserve all prior records.
            command.upgrade(config, "head")
            assert before == {
                name: connection.execute(select(table)).all() for name, table in tables.items()
            }
        return {
            "from_revision": "0008",
            "to_revision": head,
            "preserved_tables": sorted(tables),
            "legacy_allocation_zat": 100_000,
            "source_kind": "SYNTHETIC",
            "schema_removed": True,
        }
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))


if __name__ == "__main__":
    import json
    from pathlib import Path

    from zecsolve.db.session import make_engine
    from zecsolve.deployment.settings import DeploymentSettings, application_settings

    engine = make_engine(application_settings(DeploymentSettings()))
    try:
        print(json.dumps(rehearse(engine, Path.cwd())))
    finally:
        engine.dispose()
