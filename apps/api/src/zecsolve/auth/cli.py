"""Operator-only credential provisioning; invoke with python -m zecsolve.auth.cli."""

import argparse
import json
import sys
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from zecsolve.auth.credentials import issue_credential, provision_merchant, revoke_credential
from zecsolve.config import Settings
from zecsolve.db.session import make_engine


def lifetime(value: str) -> int:
    try:
        days = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Expected a whole number of days") from None
    if not 1 <= days <= 365:
        raise argparse.ArgumentTypeError("Lifetime must be 1 to 365 days")
    return days


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Provision or revoke merchant API credentials")
    commands = parser.add_subparsers(dest="action", required=True)
    create = commands.add_parser("create-merchant")
    create.add_argument("--name", required=True)
    create.add_argument("--ttl-days", type=lifetime, default=30)
    issue = commands.add_parser("issue-credential")
    issue.add_argument("--merchant-id", type=uuid.UUID, required=True)
    issue.add_argument("--ttl-days", type=lifetime, default=30)
    revoke = commands.add_parser("revoke-credential")
    revoke.add_argument("--credential-id", type=uuid.UUID, required=True)
    args = parser.parse_args(argv)

    engine = make_engine(Settings())
    try:
        with Session(engine) as session, session.begin():
            if args.action == "revoke-credential":
                revoke_credential(session, args.credential_id)
                result = {"credential_id": str(args.credential_id), "revoked": True}
            else:
                issued = (
                    provision_merchant(session, args.name, args.ttl_days)
                    if args.action == "create-merchant"
                    else issue_credential(session, args.merchant_id, args.ttl_days)
                )
                result = {
                    "merchant_id": str(issued.merchant_id),
                    "credential_id": str(issued.credential_id),
                    "expires_at": issued.expires_at.isoformat(),
                    "token": issued.token,
                }
        # This is the only credential disclosure, after the database commit succeeds.
        print(json.dumps(result))
        return 0
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    except SQLAlchemyError:
        print("Database operation failed; check connectivity and migrations", file=sys.stderr)
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
