import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session
from zecsolve.adapters.address import AddressNormalizer
from zecsolve.auth.credentials import MerchantPrincipal, provision_merchant, revoke_credential
from zecsolve.db.models import Case, CaseCreationRequest, CaseEvent
from zecsolve.schemas.case import CaseCreateRequest
from zecsolve.schemas.invoice import InvoiceCreateRequest
from zecsolve.services.invoices import InvoiceService
from zecsolve.services.workflow import WorkflowError

pytestmark = pytest.mark.postgres


@pytest.fixture
def setup_cases(database, root):
    from zecsolve.services.cases import CaseService

    with Session(database) as session, session.begin():
        issued = provision_merchant(session, "Case merchant")
    principal = MerchantPrincipal(issued.merchant_id, issued.credential_id)
    normalizer = AddressNormalizer(root / "target/debug/zecsolve-verifier")
    invoices = InvoiceService(database, normalizer, threading.BoundedSemaphore(2))
    address = json.loads((root / "fixtures/manifest.json").read_text())["expected"][
        "receiver_address"
    ]
    request = InvoiceCreateRequest(
        expected_zat=200_000,
        network="mainnet",
        pool="orchard",
        receiver_address=address,
        expected_memo="glasspane first receipt",
    )
    invoice, _ = invoices.create(principal, request, "invoice")
    return CaseService(database), principal, invoice, invoices, request


def counts(database):
    with Session(database) as session:
        return [
            session.scalar(select(func.count()).select_from(table))
            for table in (Case, CaseEvent, CaseCreationRequest)
        ]


def test_case_and_opening_event_commit_once_and_replay_original_outcome(database, setup_cases):
    service, principal, invoice, _, _ = setup_cases
    request = CaseCreateRequest(invoice_id=invoice.invoice_id)
    opened, replayed = service.create(principal, request, "case")
    assert not replayed and opened.state == "OPEN" and opened.version == 1
    assert opened.opening_event.payload["invoice_snapshot_hash"] == invoice.snapshot_hash
    assert opened.opening_event.payload["policy_id"] == str(invoice.policy_id)
    assert opened.opening_event.actor == "credential:" + str(principal.credential_id)
    assert service.create(principal, request, "case") == (opened, True)
    assert counts(database) == [1, 1, 1]
    assert service.create(principal, request, "new-key") == (opened, True)
    assert counts(database) == [1, 1, 2]
    with database.begin() as connection:
        connection.execute(
            update(Case).where(Case.id == opened.case_id).values(state="UNDER_REVIEW", version=2)
        )
    assert service.get(principal, opened.case_id).state == "UNDER_REVIEW"
    assert service.create(principal, request, "case") == (opened, True)


@pytest.mark.parametrize("same_key", [True, False])
def test_concurrent_requests_create_one_case_and_event(database, setup_cases, same_key):
    service, principal, invoice, _, _ = setup_cases
    barrier = threading.Barrier(2)
    request = CaseCreateRequest(invoice_id=invoice.invoice_id)

    def create(index):
        barrier.wait(timeout=5)
        return service.create(principal, request, "shared" if same_key else str(index))

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(create, [0, 1]))
    assert results[0][0] == results[1][0]
    assert sorted(replay for _, replay in results) == [False, True]
    assert counts(database) == [1, 1, 1 if same_key else 2]


def test_same_key_for_different_invoices_conflicts_atomically(database, setup_cases):
    service, principal, invoice, invoices, invoice_request = setup_cases
    other, _ = invoices.create(principal, invoice_request, "other-invoice")
    barrier = threading.Barrier(2)

    def create(invoice_id):
        barrier.wait(timeout=5)
        try:
            return service.create(principal, CaseCreateRequest(invoice_id=invoice_id), "conflict")
        except WorkflowError as error:
            return error.status

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(create, [invoice.invoice_id, other.invoice_id]))
    assert sum(result == 409 for result in results) == 1
    assert counts(database) == [1, 1, 1]


def test_case_and_invoice_ownership_and_revocation(database, setup_cases):
    service, principal, invoice, _, _ = setup_cases
    request = CaseCreateRequest(invoice_id=invoice.invoice_id)
    opened, _ = service.create(principal, request, "case")
    with Session(database) as session, session.begin():
        other = provision_merchant(session, "Other")
    foreign = MerchantPrincipal(other.merchant_id, other.credential_id)
    for operation in [
        lambda: service.create(foreign, request, "case"),
        lambda: service.get(foreign, opened.case_id),
        lambda: service.get(foreign, uuid.uuid4()),
    ]:
        with pytest.raises(WorkflowError) as error:
            operation()
        assert error.value.status == 404
    with Session(database) as session, session.begin():
        revoke_credential(session, principal.credential_id)
    with pytest.raises(WorkflowError) as error:
        service.create(principal, request, "case")
    assert error.value.status == 401


def test_failed_commit_leaves_no_case_event_or_retry_record(database, setup_cases):
    from sqlalchemy.exc import SQLAlchemyError

    service, principal, invoice, _, _ = setup_cases
    with database.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION reject_case_commit() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN RAISE EXCEPTION 'case test rollback'; END; $$"
            )
        )
        connection.execute(
            text(
                "CREATE CONSTRAINT TRIGGER reject_case_commit AFTER INSERT ON "
                "case_creation_requests DEFERRABLE INITIALLY DEFERRED FOR EACH ROW "
                "EXECUTE FUNCTION reject_case_commit()"
            )
        )
    with pytest.raises(SQLAlchemyError):
        service.create(principal, CaseCreateRequest(invoice_id=invoice.invoice_id), "rollback")
    assert counts(database) == [0, 0, 0]


def test_new_credential_reuses_case_without_rewriting_original_actor(database, setup_cases):
    from zecsolve.auth.credentials import issue_credential

    service, principal, invoice, _, _ = setup_cases
    request = CaseCreateRequest(invoice_id=invoice.invoice_id)
    original, _ = service.create(principal, request, "case")
    with Session(database) as session, session.begin():
        issued = issue_credential(session, principal.merchant_id)
    replacement = MerchantPrincipal(issued.merchant_id, issued.credential_id)
    assert service.create(replacement, request, "case") == (original, True)
    assert counts(database) == [1, 1, 2]


def test_legacy_case_is_not_given_a_fabricated_opening_event(database, setup_cases):
    service, principal, invoice, _, _ = setup_cases
    identity = uuid.uuid4()
    with database.begin() as connection:
        connection.execute(
            Case.__table__.insert().values(
                id=identity,
                invoice_id=invoice.invoice_id,
                merchant_id=principal.merchant_id,
                state="OPEN",
                version=1,
            )
        )
    for operation in [
        lambda: service.get(principal, identity),
        lambda: service.create(
            principal, CaseCreateRequest(invoice_id=invoice.invoice_id), "legacy"
        ),
    ]:
        with pytest.raises(WorkflowError) as error:
            operation()
        assert error.value.status == 409
    assert counts(database) == [1, 0, 0]


def test_legacy_invoice_cannot_start_a_new_workflow(database, setup_cases):
    from zecsolve.db.models import Invoice

    service, principal, _, _, _ = setup_cases
    identity = uuid.uuid4()
    with database.begin() as connection:
        connection.execute(
            Invoice.__table__.insert().values(
                id=identity,
                merchant_id=principal.merchant_id,
                network="mainnet",
                pool="orchard",
                expected_zat=1,
                expected_receiver="legacy",
                receiver_hex="00" * 43,
                snapshot_hash="ab" * 32,
                policy_version="legacy",
            )
        )
    with pytest.raises(WorkflowError) as error:
        service.create(principal, CaseCreateRequest(invoice_id=identity), "legacy-invoice")
    assert error.value.status == 409
    assert error.value.code == "LEGACY_INVOICE_POLICY_UNAVAILABLE"
    assert counts(database) == [0, 0, 0]


def test_event_and_retry_record_are_immutable(database, setup_cases):
    from sqlalchemy.exc import DBAPIError

    service, principal, invoice, _, _ = setup_cases
    service.create(principal, CaseCreateRequest(invoice_id=invoice.invoice_id), "immutable")
    for model in [CaseEvent, CaseCreationRequest]:
        for operation in [
            model.__table__.delete(),
            model.__table__.update().values(id=uuid.uuid4()),
        ]:
            with pytest.raises(DBAPIError, match="immutable record"):
                with database.begin() as connection:
                    connection.execute(operation)


def test_expiry_during_invoice_lock_wait_blocks_case_creation(database, setup_cases):
    import time
    from datetime import timedelta

    from zecsolve.db.models import Invoice, MerchantCredential

    service, principal, invoice, _, _ = setup_cases
    with database.begin() as connection:
        now = connection.scalar(select(func.clock_timestamp()))
        connection.execute(
            update(MerchantCredential)
            .where(MerchantCredential.id == principal.credential_id)
            .values(expires_at=now + timedelta(seconds=2))
        )
    with ThreadPoolExecutor(max_workers=1) as executor:
        with database.begin() as blocker:
            blocker.execute(
                select(Invoice).where(Invoice.id == invoice.invoice_id).with_for_update()
            )
            future = executor.submit(
                service.create,
                principal,
                CaseCreateRequest(invoice_id=invoice.invoice_id),
                "expiry",
            )
            deadline = time.monotonic() + 1
            with database.connect().execution_options(isolation_level="AUTOCOMMIT") as observer:
                while not observer.scalar(
                    text(
                        "SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                        "WHERE wait_event_type='Lock' AND query LIKE '%invoices%')"
                    )
                ):
                    assert time.monotonic() < deadline, "Request did not wait for invoice lock"
                    time.sleep(0.01)
            time.sleep(2.1)
        with pytest.raises(WorkflowError) as error:
            future.result(timeout=5)
        assert error.value.status == 401
    assert counts(database) == [0, 0, 0]


def test_case_evidence_blocks_destructive_downgrade(database, root, setup_cases):
    from alembic import command
    from alembic.config import Config

    service, principal, invoice, _, _ = setup_cases
    opened, _ = service.create(principal, CaseCreateRequest(invoice_id=invoice.invoice_id), "case")
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "apps/api/migrations"))
    with pytest.raises(RuntimeError, match="forward migration"):
        with database.begin() as connection:
            config.attributes["connection"] = connection
            command.downgrade(config, "0003")
    assert service.get(principal, opened.case_id).opening_event == opened.opening_event


def test_downgrade_cannot_erase_an_inflight_case(database, root, setup_cases):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import event

    service, principal, invoice, _, _ = setup_cases
    paused = threading.Event()
    release = threading.Event()
    role = threading.local()

    def coordinate(connection, cursor, statement, parameters, context, executemany):
        statement = statement.lstrip()
        if (
            getattr(role, "name", None) == "writer"
            and "FROM invoices" in statement
            and "FOR UPDATE" in statement
        ):
            paused.set()
            assert release.wait(timeout=5), "Downgrade did not reach its serialization point"
        if getattr(role, "name", None) == "migration" and (
            statement.startswith("DROP TABLE case_creation_requests")
            or statement.startswith("LOCK TABLE case_creation_requests")
        ):
            release.set()

    def create():
        role.name = "writer"
        return service.create(
            principal, CaseCreateRequest(invoice_id=invoice.invoice_id), "inflight"
        )

    def downgrade():
        role.name = "migration"
        config = Config(str(root / "alembic.ini"))
        config.set_main_option("script_location", str(root / "apps/api/migrations"))
        try:
            with database.begin() as connection:
                config.attributes["connection"] = connection
                command.downgrade(config, "0003")
            return "downgraded"
        except RuntimeError as error:
            return str(error)

    event.listen(database, "before_cursor_execute", coordinate)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            writer = executor.submit(create)
            assert paused.wait(timeout=5)
            migration = executor.submit(downgrade)
            opened, _ = writer.result(timeout=10)
            assert "forward migration" in migration.result(timeout=10)
    finally:
        release.set()
        event.remove(database, "before_cursor_execute", coordinate)
    assert service.get(principal, opened.case_id).opening_event == opened.opening_event
    assert counts(database) == [1, 1, 1]
