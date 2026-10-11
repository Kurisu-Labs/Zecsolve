import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session
from zecsolve.adapters.address import AddressNormalizer
from zecsolve.auth.credentials import MerchantPrincipal, provision_merchant, revoke_credential
from zecsolve.db.models import Invoice, InvoiceCreationRequest, InvoicePolicy
from zecsolve.schemas.invoice import InvoiceCreateRequest

pytestmark = pytest.mark.postgres


@pytest.fixture
def invoice_request(root):
    manifest = json.loads((root / "fixtures/manifest.json").read_text())
    return InvoiceCreateRequest(
        expected_zat=200_000,
        network="mainnet",
        pool="orchard",
        receiver_address=manifest["expected"]["receiver_address"],
        expected_memo="glasspane first receipt",
    )


@pytest.fixture
def principal(database):
    with Session(database) as session, session.begin():
        issued = provision_merchant(session, "Invoice test")
    return MerchantPrincipal(issued.merchant_id, issued.credential_id)


@pytest.fixture
def service(database, root):
    from zecsolve.services.invoices import InvoiceService

    return InvoiceService(
        database,
        AddressNormalizer(root / "target/debug/zecsolve-verifier"),
        threading.BoundedSemaphore(2),
    )


def counts(database):
    with Session(database) as session:
        return [
            session.scalar(select(func.count()).select_from(table))
            for table in (Invoice, InvoicePolicy, InvoiceCreationRequest)
        ]


def test_create_persists_owned_snapshot_and_retries_without_normalizing(
    database, service, principal, invoice_request, report
):
    snapshot, replayed = service.create(principal, invoice_request, "first")
    assert not replayed
    assert snapshot.merchant_id == principal.merchant_id
    assert snapshot.terms.receiver_hex == report.output.receiver_hex
    assert snapshot.terms.memo_hex == report.output.memo_hex
    assert snapshot.policy.minimum_confirmations == 10
    service.normalizer.binary = service.normalizer.binary.parent / "absent"
    retry, replayed = service.create(principal, invoice_request, "first")
    assert replayed and retry == snapshot
    assert service.get(principal, snapshot.invoice_id) == snapshot
    assert counts(database) == [1, 1, 1]


def test_same_key_different_body_conflicts_and_foreign_invoice_is_hidden(
    database, service, principal, invoice_request
):
    from zecsolve.services.invoices import InvoiceError

    snapshot, _ = service.create(principal, invoice_request, "first")
    with pytest.raises(InvoiceError) as error:
        service.create(principal, invoice_request.model_copy(update={"expected_zat": 1}), "first")
    assert error.value.status == 409
    with Session(database) as session, session.begin():
        other = provision_merchant(session, "Other")
    other = MerchantPrincipal(other.merchant_id, other.credential_id)
    for invoice_id in [snapshot.invoice_id, uuid.uuid4()]:
        with pytest.raises(InvoiceError) as error:
            service.get(other, invoice_id)
        assert error.value.status == 404
    second, replayed = service.create(other, invoice_request, "first")
    assert not replayed and second.invoice_id != snapshot.invoice_id
    assert counts(database) == [2, 2, 2]


def test_concurrent_same_key_commits_exactly_one_invoice(
    database, service, principal, invoice_request
):
    barrier = threading.Barrier(2)
    normalize = service.normalizer.normalize

    def synchronize(request):
        result = normalize(request)
        barrier.wait(timeout=5)
        return result

    service.normalizer.normalize = synchronize
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(service.create, principal, invoice_request, "race") for _ in range(2)
        ]
        results = [future.result(timeout=10) for future in futures]
    assert sorted(replayed for _, replayed in results) == [False, True]
    assert results[0][0] == results[1][0]
    assert counts(database) == [1, 1, 1]


def test_revocation_during_normalization_blocks_all_writes(
    database, service, principal, invoice_request
):
    from zecsolve.services.invoices import InvoiceError

    normalize = service.normalizer.normalize

    def revoke_then_normalize(request):
        with Session(database) as session, session.begin():
            revoke_credential(session, principal.credential_id)
        return normalize(request)

    service.normalizer.normalize = revoke_then_normalize
    with pytest.raises(InvoiceError) as error:
        service.create(principal, invoice_request, "revoked")
    assert error.value.status == 401
    assert counts(database) == [0, 0, 0]


def test_failed_commit_rolls_back_policy_invoice_and_retry_record(
    database, service, principal, invoice_request
):
    from sqlalchemy.exc import SQLAlchemyError

    with database.begin() as connection:
        connection.execute(
            text(
                "CREATE FUNCTION fail_invoice_commit() RETURNS trigger LANGUAGE plpgsql AS $$ "
                "BEGIN RAISE EXCEPTION 'test rollback'; END; $$"
            )
        )
        connection.execute(
            text(
                "CREATE CONSTRAINT TRIGGER fail_invoice_commit AFTER INSERT ON "
                "invoice_creation_requests DEFERRABLE INITIALLY DEFERRED "
                "FOR EACH ROW EXECUTE FUNCTION fail_invoice_commit()"
            )
        )
    with pytest.raises(SQLAlchemyError):
        service.create(principal, invoice_request, "rollback")
    assert counts(database) == [0, 0, 0]


def test_invalid_address_and_expired_invoice_create_nothing(
    database, service, principal, invoice_request
):
    from datetime import UTC, datetime

    from zecsolve.services.invoices import InvoiceError

    for request in [
        invoice_request.model_copy(update={"receiver_address": "bad"}),
        invoice_request.model_copy(update={"expires_at": datetime(2000, 1, 1, tzinfo=UTC)}),
    ]:
        with pytest.raises(InvoiceError) as error:
            service.create(principal, request, "invalid")
        assert error.value.status == 422
    assert counts(database) == [0, 0, 0]
