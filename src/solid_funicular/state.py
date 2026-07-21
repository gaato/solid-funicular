import json
import os
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


class JsonState:
    def __init__(self, local_path: str, object_name: str) -> None:
        self.local_path = local_path
        self.object_name = object_name
        self.backend = os.environ.get("BOT_STATE_BACKEND", "local")
        if self.backend not in {"local", "s3"}:
            raise RuntimeError('BOT_STATE_BACKEND must be either "local" or "s3"')
        self.endpoint = os.environ.get("S3_ENDPOINT")
        self.region = os.environ.get("S3_REGION")
        self.bucket = os.environ.get("S3_BUCKET")
        self.access_key_id = os.environ.get("S3_ACCESS_KEY_ID")
        self.secret_access_key = os.environ.get("S3_SECRET_ACCESS_KEY")
        self.prefix = os.environ.get("BOT_STATE_PREFIX", "").strip("/")
        self._client = None
        if self.backend == "s3":
            missing = [
                name
                for name, value in {
                    "S3_ENDPOINT": self.endpoint,
                    "S3_REGION": self.region,
                    "S3_BUCKET": self.bucket,
                    "S3_ACCESS_KEY_ID": self.access_key_id,
                    "S3_SECRET_ACCESS_KEY": self.secret_access_key,
                }.items()
                if not value
            ]
            if missing:
                raise RuntimeError(
                    f'{", ".join(missing)} must be set when BOT_STATE_BACKEND=s3'
                )

    @property
    def key(self) -> str:
        if self.prefix:
            return f"{self.prefix}/{self.object_name}"
        return self.object_name

    @property
    def client(self):
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint,
                region_name=self.region,
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                config=Config(s3={"addressing_style": "path"}),
            )
        return self._client

    def load(self) -> dict[str, Any]:
        if self.backend != "s3":
            return self._load_local()
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=self.key)
        except ClientError as error:
            code = error.response.get("Error", {}).get("Code")
            if code not in {"404", "NoSuchKey"}:
                raise
            data: dict[str, Any] = {}
            self.save(data)
            return data
        return json.loads(response["Body"].read().decode("utf-8"))

    def save(self, data: dict[str, Any]) -> None:
        if self.backend != "s3":
            self._save_local(data)
            return
        self.client.put_object(
            Bucket=self.bucket,
            Key=self.key,
            Body=json.dumps(data).encode("utf-8"),
            ContentType="application/json",
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
