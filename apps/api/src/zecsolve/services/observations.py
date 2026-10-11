import uuid

from pydantic import ValidationError

from zecsolve.adapters.chain import OfflineObserver, unavailable_observation
from zecsolve.db.models import ChainObservation
from zecsolve.schemas.resolution import DecisionObservationV1, observation_adapter
from zecsolve.services.verification_records import read_attempt
from zecsolve.services.workflow import WorkflowError, authorize_merchant, transaction


def read_decision_observation(session, principal, case_id, observation_id):
    row = session.get(ChainObservation, observation_id)
    if row is None or (row.case_id, row.merchant_id) != (case_id, principal.merchant_id):
        raise WorkflowError(404, "OBSERVATION_NOT_FOUND")
    try:
        obs = observation_adapter.validate_python(row.provenance)
        if (
            obs.observation_id,
            obs.verification_id,
            obs.state,
            obs.source,
            obs.observed_at,
            obs.confirmations,
            obs.block_hash,
            obs.block_height,
        ) != (
            row.id,
            row.verification_id,
            row.state,
            row.source,
            row.observed_at,
            row.confirmations,
            row.block_hash,
            row.block_height,
        ):
            raise ValueError("Observation metadata mismatch")
        return obs
    except (ValueError, ValidationError):
        raise WorkflowError(409, "OBSERVATION_HISTORY_UNAVAILABLE") from None


class ObservationService:
    def __init__(self, engine, observer=None):
        self.engine = engine
        self.observer = observer if observer is not None else OfflineObserver()

    def refresh(self, principal, case_id, verification_id):
        with transaction(self.engine) as session:
            authorize_merchant(session, principal)
            attempt = read_attempt(session, principal, case_id, verification_id)
            authorize_merchant(session, principal)
        report = attempt.result
        network = report.output.network if report.output else "mainnet"
        txid = report.output.txid if report.output else None
        # External work occurs without a database transaction. Failure is a new diagnostic.
        try:
            data = self.observer.observe(network, txid, report.raw_tx_sha256)
            observation = observation_adapter.validate_python(
                dict(data)
                | {
                    "observation_id": uuid.uuid4(),
                    "verification_id": verification_id,
                }
            )
        except (OSError, TimeoutError, ValueError, TypeError):
            observation = DecisionObservationV1(
                observation_id=uuid.uuid4(),
                verification_id=verification_id,
                **unavailable_observation(network, txid, report.raw_tx_sha256, "OBSERVER_FAILED"),
            )
        with transaction(self.engine) as session:
            authorize_merchant(session, principal)
            read_attempt(session, principal, case_id, verification_id)
            session.add(
                ChainObservation(
                    id=observation.observation_id,
                    verification_id=verification_id,
                    case_id=case_id,
                    merchant_id=principal.merchant_id,
                    state=observation.state,
                    source=observation.source,
                    observed_at=observation.observed_at,
                    block_hash=observation.block_hash,
                    block_height=observation.block_height,
                    confirmations=observation.confirmations,
                    provenance=observation.model_dump(mode="json"),
                )
            )
            authorize_merchant(session, principal)
        return observation
