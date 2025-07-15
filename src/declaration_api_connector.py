import base64
import hashlib
import json
import logging
import subprocess
import time
from types import SimpleNamespace

import jwt
import multihash
import requests
from base58 import b58encode

logger = logging.getLogger(__name__)


class DeclarationApiConnector:
    def __init__(
        self,
        dry: bool,
        api_endpoint: str,
        api_key: str,
        member_credentials_path: str,
        private_key_path: str
    ):
        self._dry = dry
        self._member_credentials = (self._read_json(member_credentials_path)
                                    .get("verifiableCredential"))
        self._private_key = self._read_text(private_key_path)
        self._api_endpoint = api_endpoint
        self._api_key = api_key

    def _read_json(self, path: str) -> dict:
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            raise ReadFileError(path)

    def _read_text(self, path: str) -> str:
        try:
            with open(path) as f:
                return f.read()
        except Exception:
            raise ReadFileError(path)

    def request_declaration(
        self,
        name: str,
        iscc: str,
        location: str,
        rights_statement: str
    ):
        # Epoch time in milliseconds.
        timestamp = int(time.time() * 1000)
        public_metadata = {
            "iscc": iscc,
            "name": name,
            "original": True,
            "version": 0,
            "timestamp": timestamp,
            "credentials": [self._member_credentials],
            "supplierData": {
                "location": location,
                "rightsStatement": rights_statement,
            }
        }
        proof = self._member_credentials.get("proof").get("jwt")
        commons_db_metadata = {
            "location": location,
            "rightsStatement": rights_statement,
            "iscc": iscc,
            "credentials": [{"proof": proof}],
            "timestamp": timestamp
        }
        data = {
            "signature": self._get_signature(public_metadata),
            "tsaSignature": self._get_tsa(public_metadata, "tsa"),
            "declarationMetadata": {
                "publicMetadata": public_metadata,
                "commonsDbRegistry": commons_db_metadata
            },
            "commonsDbRegistrySignature":
                self._get_signature(commons_db_metadata),
            "commonsDbRegistryTsaSignature":
                self._get_tsa(commons_db_metadata, "commons-db-tsa")
        }
        headers = {
            "User-Agent": "commonsdb-commons-supplier/0.0.1",
            "Authorization": f"Bearer {self._api_key}",
        }
        logger.info(f"Sending request to '{self._api_endpoint}'.")
        logger.debug(f"POST: {json.dumps(data)}")
        if self._dry:
            response = SimpleNamespace(text="DRY RESPONSE")
        else:
            response = requests.post(
                self._api_endpoint, json=data, headers=headers)
        logger.debug(f"Received response: {response.text}")

    def _get_cid(self, public_metadata: str) -> str:
        json_string = json.dumps(
            public_metadata,
            separators=(',', ':'),
            sort_keys=True
        )
        hash = hashlib.sha256((json_string.encode()))
        prefix = bytes([0x12, 0x20])
        mh = multihash.encode(hash.digest(), "sha2-256")
        cid = b"".join([prefix, mh])
        return b58encode(cid).decode()

    def _get_declaration_id(self, public_metadata: str, cid: str) -> str:
        cid_hash = hashlib.sha256(cid.encode()).digest()

        ids = b"".join([
            bytes.fromhex(public_metadata.get("declarationIdVersion")),
            bytes.fromhex(public_metadata.get("regId")),
            cid_hash
        ])
        declaration_id = b58encode(ids)[:20].lower()
        return declaration_id.decode()

    def _get_signature(self, data: str) -> str:
        signature = jwt.encode(
            data,
            self._private_key,
            algorithm="ES256"
        )
        return signature

    def _get_tsa(self, data: dict, name: str) -> dict:
        # TODO: Do this without having to juggle files.
        with open(f"{name}.json", "w") as data_file:
            json.dump(data, data_file)

        # TODO: Is there a library that does this instead?
        openssl_command = [
            "openssl",
            "ts",
            "-query",
            "-data",
            f"{name}.json",
            "-no_nonce",
            "-sha512",
            "-cert",
            "-out",
            f"{name}.tsq"
        ]
        subprocess.run(openssl_command)

        headers = {"Content-Type": "application/timestamp-query"}
        with open(f"{name}.tsq", "rb") as tsq_file:
            tsq_data = tsq_file.read()
            r = requests.post(
                "https://freetsa.org/tsr",
                data=tsq_data,
                headers=headers
            )
            tsq = base64.b64encode(tsq_data).decode()

        tsr = base64.b64encode(r.content).decode()
        with open(f"{name}.tsr", "wb") as tsr_file:
            tsr_file.write(r.content)

        return {"tsq": tsq, "tsr": tsr}


class ReadFileError(Exception):
    def __init__(self, path):
        super().__init__(f"Failed reading file: '{path}'")
