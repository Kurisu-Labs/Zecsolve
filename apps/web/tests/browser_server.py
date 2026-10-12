"""Local-only browser acceptance server using the actual deployment app and PostgreSQL.

Requires a disposable database URL and an external scratch directory. No fake API
routes or verifier results are installed. Credentials stay in the scratch file.
"""

import base64
import datetime
import ipaddress
import json
import os
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from zecsolve.auth.credentials import provision_merchant
from zecsolve.config import Settings
from zecsolve.deployment.app import create_app
from zecsolve.deployment.settings import DeploymentSettings

ROOT = Path(__file__).resolve().parents[3]
scratch = Path(os.environ['ZECSOLVE_BROWSER_SCRATCH']).resolve()
scratch.mkdir(parents=True, exist_ok=True)
url = os.environ['ZECSOLVE_TEST_DATABASE_URL']
if not url.rsplit('/', 1)[-1].endswith('_browser'):
    raise ValueError('Use a dedicated disposable database ending in _browser')
engine = create_engine(url)
config = Config(str(ROOT / 'alembic.ini'))
config.set_main_option('script_location', str(ROOT / 'apps/api/migrations'))
with engine.begin() as connection:
    config.attributes['connection'] = connection
    command.upgrade(config, 'head')
with Session(engine) as session, session.begin():
    merchant = provision_merchant(session, 'Public fixture browser acceptance')
key_path = scratch / 'evidence-key.txt'
if not key_path.exists():
    key_path.write_text(base64.b64encode(os.urandom(32)).decode())
(scratch / 'state.json').write_text(json.dumps({'merchant_code': merchant.token}))
engine.dispose()
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
now = datetime.datetime.now(datetime.UTC)
cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=2))
        .add_extension(x509.SubjectAlternativeName([
            x509.DNSName('localhost'), x509.IPAddress(ipaddress.ip_address('127.0.0.1')),
        ]), critical=False).sign(key, hashes.SHA256()))
(scratch / 'tls.key').write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
(scratch / 'tls.crt').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
settings = Settings(_env_file=None, database_url=url, browser_origins=['https://localhost:8443'],
                    verifier_path=Path(os.environ.get('ZECSOLVE_BROWSER_VERIFIER', ROOT / 'target/debug/zecsolve-verifier.exe')),
                    migrations_path=ROOT / 'apps/api/migrations', evidence_key_id='browser-fixture',
                    evidence_key=key_path.read_text())
app = create_app(settings, DeploymentSettings(host='localhost', web_dist=ROOT / 'apps/web/dist'))
uvicorn.run(app, host='127.0.0.1', port=8443, ssl_keyfile=str(scratch / 'tls.key'),
            ssl_certfile=str(scratch / 'tls.crt'), access_log=False)
