import uuid

from zecsolve.schemas.verification import Contract


class MerchantIdentity(Contract):
    merchant_id: uuid.UUID
    credential_id: uuid.UUID
