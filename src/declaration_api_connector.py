import base64
import json
import logging
import subprocess
from time import sleep, time
from types import SimpleNamespace

import jwt
import requests
from jwcrypto.jwk import JWK

logger = logging.getLogger(__name__)


class DeclarationApiConnector:
    def __init__(
        self,
        dry: bool,
        api_endpoint: str,
        api_key: str,
        member_credentials_path: str,
        private_key_path: str,
        public_key_path: str,
        rate_limit: float = 0
    ):
        self._dry = dry
        self._member_credentials = (self._read_json(member_credentials_path)
                                    .get("verifiableCredential"))
        self._private_key = self._read_text(private_key_path)
        self._public_key = self._read_text(public_key_path).encode("utf-8")
        self._api_endpoint = api_endpoint
        self._api_key = api_key
        self._rate_limit = rate_limit

        self._last_request_time = None

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
        rights_statement: str,
        extra_public_metadata: dict
    ) -> str | None:
        if self._member_credentials is None:
            raise Exception("Invalid memeber credentials.")

        # Epoch time in milliseconds.
        timestamp = int(time() * 1000)
        public_metadata = {
            "$schema": "https://w3id.org/commonsdb/schema/0.2.0.json",
            "@context": "https://w3id.org/commonsdb/context/0.2.0.json",
            "declarerId": self._member_credentials.get("credentialSubject").get("id"),
            "iscc": iscc,
            "name": name,
            "original": True,
            "version": 1,
            "timestamp": timestamp,
            "credentials": [self._member_credentials],
            "supplierData": {
                "location": location,
                "rightsStatement": rights_statement,
            }
        }
        public_metadata.update(extra_public_metadata)
        proof = self._member_credentials.get("proof").get("jwt")
        commons_db_metadata = {
            "location": location,
            "rightsStatement": rights_statement,
            "iscc": iscc,
            "credentials": [{"proof": proof}],
            "timestamp": timestamp
        }
        signature = self._get_signature(public_metadata)
        cdbSignature = self._get_signature(commons_db_metadata)
        data = {
            "signature": signature,
            "tsaSignature": self._get_tsa(signature, "tsa"),
            "declarationMetadata": {
                "publicMetadata": public_metadata,
                "commonsDbRegistry": commons_db_metadata
            },
            "commonsDbRegistrySignature": cdbSignature,
            "commonsDbRegistryTsaSignature":
                self._get_tsa(cdbSignature, "commons-db-tsa")
        }
        headers = {
            "User-Agent": "commonsdb-commons-supplier/0.1.9",
            "Authorization": f"Bearer {self._api_key}",
        }
        logger.info(f"Sending request to '{self._api_endpoint}'.")
        logger.debug(f"POST: {json.dumps(data)}")
        if self._rate_limit and self._last_request_time:
            time_since_last = time() - self._last_request_time
            if time_since_last < self._rate_limit:
                wait_time = self._rate_limit - time_since_last
                logger.debug(
                    f"Waiting {wait_time} seconds for rate limit.")
                sleep(wait_time)
        self._last_request_time = time()
        old_cid = public_metadata.get("supersedes")
        if self._dry:
            def dry_json():
                if old_cid:
                    return {"cidV1": "cid456"}
                else:
                    return {"cidV1": "cid123"}
            response = SimpleNamespace(
                text="DRY RESPONSE",
                json=dry_json
            )
            response.ok = True
        else:
            response = requests.post(
                self._api_endpoint, json=data, headers=headers)
        logger.debug(f"Received response: {response.text}")

        response_content = response.json()
        if not response.ok:
            logger.error(f"Response code is non OK: {response.status_code}.")
            if response.status_code == 422:
                for validation_error in response_content.get("validationErrors"):
                    logger.error(validation_error)
            raise Exception("Invalid declaration. See response above for details.")

        new_cid = response_content.get("cidV1")
        if old_cid:
            logger.info(
                f"Update declaration CID(old): {new_cid}({old_cid})"
            )
        else:
            logger.info(f"New declaration CID: {new_cid}")

        return new_cid

    def _get_signature(self, data: dict) -> str:
        jwk = JWK.from_pem(self._public_key).export(as_dict=True)
        headers = {
            "jwk": jwk,
            "alg": "ES256",
            "typ": "JWT",
        }
        signature = jwt.encode(
            data,
            self._private_key,
            headers=headers,
            algorithm="ES256"
        )
        return signature

    def _get_tsa(self, data: str, name: str) -> dict:
        # TODO: Do this without having to juggle files.
        with open(f"tmp/{name}.txt", "w") as data_file:
            data_file.write(data)

        # TODO: Is there a library that does this instead?
        openssl_command = [
            "openssl",
            "ts",
            "-query",
            "-data",
            f"tmp/{name}.txt",
            "-no_nonce",
            "-sha512",
            "-cert",
            "-out",
            f"tmp/{name}.tsq"
        ]
        subprocess.run(openssl_command)

        headers = {"Content-Type": "application/timestamp-query"}
        with open(f"tmp/{name}.tsq", "rb") as tsq_file:
            tsq = tsq_file.read()
        tsq_b64 = base64.b64encode(tsq).decode()
        r = requests.post(
            "https://freetsa.org/tsr",
            data=tsq,
            headers=headers
        )
        tsr = r.content
        tsr_b64 = base64.b64encode(tsr).decode()

        # Save to file if you want to verify easily.
        with open(f"tmp/{name}.tsr", "wb") as tsr_file:
            tsr_file.write(r.content)

        return {"tsq": tsq_b64, "tsr": tsr_b64}


class ReadFileError(Exception):
    def __init__(self, path):
        super().__init__(f"Failed reading file: '{path}'")
