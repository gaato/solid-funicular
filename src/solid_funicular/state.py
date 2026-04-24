import json
import os
from typing import Any

import oci
from oci.exceptions import ServiceError


class JsonState:
    def __init__(self, local_path: str, object_name: str) -> None:
        self.local_path = local_path
        self.object_name = object_name
        self.backend = os.environ.get("BOT_STATE_BACKEND", "local")
        self.bucket = os.environ.get("BOT_STATE_BUCKET")
        self.namespace = os.environ.get("BOT_STATE_NAMESPACE")
        self.prefix = os.environ.get("BOT_STATE_PREFIX", "").strip("/")
        self._client = None

    @property
    def key(self) -> str:
        if self.prefix:
            return f"{self.prefix}/{self.object_name}"
        return self.object_name

    @property
    def client(self):
        if self._client is None:
            self._client = oci.object_storage.ObjectStorageClient(self._oci_config())
        return self._client

    def _oci_config(self) -> dict[str, str]:
        key_content = os.environ.get("OCI_PRIVATE_KEY")
        if key_content:
            return {
                "user": os.environ["OCI_USER_OCID"],
                "fingerprint": os.environ["OCI_FINGERPRINT"],
                "tenancy": os.environ["OCI_TENANCY_OCID"],
                "region": os.environ["OCI_REGION"],
                "key_content": key_content,
                **(
                    {"pass_phrase": os.environ["OCI_PRIVATE_KEY_PASSPHRASE"]}
                    if os.environ.get("OCI_PRIVATE_KEY_PASSPHRASE")
                    else {}
                ),
            }
        return oci.config.from_file()

    def load(self) -> dict[str, Any]:
        if self.backend != "oci":
            return self._load_local()
        if not self.bucket or not self.namespace:
            raise RuntimeError(
                "BOT_STATE_BUCKET and BOT_STATE_NAMESPACE are required when BOT_STATE_BACKEND=oci"
            )
        try:
            response = self.client.get_object(self.namespace, self.bucket, self.key)
        except ServiceError as error:
            if error.status != 404:
                raise
            data: dict[str, Any] = {}
            self.save(data)
            return data
        return json.loads(response.data.content.decode("utf-8"))

    def save(self, data: dict[str, Any]) -> None:
        if self.backend != "oci":
            self._save_local(data)
            return
        if not self.bucket or not self.namespace:
            raise RuntimeError(
                "BOT_STATE_BUCKET and BOT_STATE_NAMESPACE are required when BOT_STATE_BACKEND=oci"
            )
        self.client.put_object(
            self.namespace,
            self.bucket,
            self.key,
            json.dumps(data).encode("utf-8"),
            content_type="application/json",
        )

    def _load_local(self) -> dict[str, Any]:
        if not os.path.exists(self.local_path):
            self._save_local({})
            return {}
        with open(self.local_path, "r") as f:
            return json.load(f)

    def _save_local(self, data: dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.local_path), exist_ok=True)
        with open(self.local_path, "w") as f:
            json.dump(data, f)
