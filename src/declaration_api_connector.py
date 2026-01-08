import base64
import hashlib
import json
import logging
import subprocess
from time import sleep, time
from types import SimpleNamespace

import jwt
import multihash
import requests
from base58 import b58encode
from jwcrypto.jwk import JWK
from pythonodejs import node_eval

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
            "declarerId": "did:tmp:abc123",
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
        # print("========")
        # print(self._get_signature(public_metadata))
        # print("========")
        # raise Exception("STOP")
        signature = self._get_signature(public_metadata)
        cdbSignature = self._get_signature(commons_db_metadata)
        data = {
            "signature": signature,
            "tsaSignature": self._get_tsa(signature, "tsa"),
            "declarationMetadata": {
                "publicMetadata": public_metadata,
                "commonsDbRegistry": commons_db_metadata
            },
            "commonsDbRegistrySignature":
                cdbSignature,
            "commonsDbRegistryTsaSignature":
                self._get_tsa(cdbSignature, "commons-db-tsa")
        }
        headers = {
            "User-Agent": "commonsdb-commons-supplier/0.0.1",
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
                    return {"message": "ingested", "cidV1": "cid456"}
                else:
                    return {"message": "ingested", "cidV1": "cid123"}
            response = SimpleNamespace(
                text="DRY RESPONSE",
                json=dry_json
            )
        else:
            response = requests.post(
                self._api_endpoint, json=data, headers=headers)
        logger.debug(f"Received response: {response.text}")

        response_content = response.json()
        message = response_content.get("message")
        if not response.ok:
            logger.error(f"Response code is non OK: {response.status_code}.")
            if response.status_code == 422:
                for validation_error in response_content.get("validationErrors"):
                    logger.error(validation_error)
            raise Exception("Invalid declaration.")

        elif message == "ingested":
            new_cid = response_content.get("cidV1")
            if old_cid:
                logger.info(
                    f"Update declaration CID(old): {new_cid}({old_cid})"
                )
            else:
                logger.info(f"New declaration CID: {new_cid}")
            return new_cid
        else:
            logger.warning(f"Unexpected message in response: '{message}'.")

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

    def _get_tsa(self, data, name: str) -> dict:
        # command = ["dev/tsa.sh", data]
        # subprocess.run(command)
        # with open(f"{name}.tsq", "rb") as tsq_file:
        #     tsq_data = tsq_file.read()
        #     tsq = base64.b64encode(tsq_data).decode()
        # print(tsq)

        # with open(f"{name}.tsr", "rb") as tsr_file:
        #     tsr_data = tsr_file.read()
        #     tsr = base64.b64encode(tsr_data).decode()
        # print(tsr)

        # return {"tsq": tsq, "tsr": tsr}
        
        # TODO: Do this without having to juggle files.
        with open(f"{name}.json", "w") as data_file:
            data_file.write(data)
            # json.dump(data, data_file)

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
            tsq = tsq_file.read()
        # node_tsq = subprocess.run(["node", "tsa.ts", data], cwd="../node", capture_output=True).stdout.strip().decode()
        node_tsq = make_tsa_node(data)
        tsq_b64 = node_tsq
        # tsq_b64 = node_tsq
        print("=" * 50)
        print(node_tsq)
        print(tsq)
        r = requests.post(
            "https://freetsa.org/tsr",
            data=base64.b64decode(tsq_b64),
            headers=headers
        )
        tsr = r.content
        tsr_b64 = base64.b64encode(tsr).decode()
        print("-" * 50)
        print(base64.b64decode(tsr_b64))
        print("=" * 50)

        # Save to file if you want to verify easily.
        with open(f"{name}.tsr", "wb") as tsr_file:
            tsr_file.write(r.content)

        return {"tsq": tsq_b64, "tsr": tsr_b64}


make_tsa_node = node_eval("""
    function tsa(data) {
  const crypto = require('crypto');

  const hash = crypto.createHash("sha512").update(data).digest();

  const hashAlgorithmOid = Buffer.from([
    0x06, 0x09, 0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x03,
  ]);
  const algorithmIdentifier = Buffer.concat([
    Buffer.from([0x30, hashAlgorithmOid.length]),
    hashAlgorithmOid,
  ]);

  const hashedMessage = Buffer.concat([
    Buffer.from([0x04, hash.length]),
    hash,
  ]);

  const messageImprint = Buffer.concat([
    Buffer.from([0x30, algorithmIdentifier.length + hashedMessage.length]),
    algorithmIdentifier,
    hashedMessage,
  ]);

  const version = Buffer.from([0x02, 0x01, 0x01]);
  const tsReqContent = Buffer.concat([version, messageImprint]);
  const tsReq = Buffer.concat([
    Buffer.from([0x30, tsReqContent.length]),
    tsReqContent,
  ]);

  const tsqBase64 = tsReq.toString("base64");

  return tsqBase64;
  }
  
  tsa;
    """)

def create_timestamp_request(data) -> bytes:
    """
    Creates a Time-Stamp Protocol (TSP) request according to RFC 3161.
    
    Args:
        data: The data to be timestamped. Can be bytes or string.
    
    Returns:
        The complete TSP request as bytes.
    """
    # Convert string to bytes if necessary
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    # Step 1: Create SHA-512 hash of the data
    hash_obj = hashlib.sha512(data)
    hash_bytes = hash_obj.digest()
    
    # Step 2: Create hash algorithm OID (SHA-512 OID: 2.16.840.1.101.3.4.2.3)
    # OID: 2.16.840.1.101.3.4.2.3 in ASN.1 DER encoding
    hash_algorithm_oid = bytes([
        0x06, 0x09, 0x60, 0x86, 0x48, 0x01, 0x65, 0x03, 0x04, 0x02, 0x03,
    ])
    
    # Step 3: Create AlgorithmIdentifier SEQUENCE
    # 0x30 = SEQUENCE tag, followed by length
    algorithm_identifier = bytes([0x30, len(hash_algorithm_oid)]) + hash_algorithm_oid
    
    # Step 4: Create hashedMessage OCTET STRING
    # 0x04 = OCTET STRING tag, followed by length
    hashed_message = bytes([0x04, len(hash_bytes)]) + hash_bytes
    
    # Step 5: Create MessageImprint SEQUENCE
    message_imprint_length = len(algorithm_identifier) + len(hashed_message)
    message_imprint = bytes([0x30, message_imprint_length]) + algorithm_identifier + hashed_message
    
    # Step 6: Create version INTEGER (v1)
    version = bytes([0x02, 0x01, 0x01])  # INTEGER tag (0x02), length 1, value 1
    
    # Step 7: Create TimeStampReqContent SEQUENCE
    ts_req_content = version + message_imprint
    
    # Step 8: Create final TimeStampReq SEQUENCE
    ts_req = bytes([0x30, len(ts_req_content)]) + ts_req_content
    
    return ts_req


class ReadFileError(Exception):
    def __init__(self, path):
        super().__init__(f"Failed reading file: '{path}'")
