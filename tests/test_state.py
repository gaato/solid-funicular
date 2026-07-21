import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError

from solid_funicular.state import JsonState


S3_ENV = {
    "BOT_STATE_BACKEND": "s3",
    "BOT_STATE_PREFIX": "/bots/solid-funicular/",
    "S3_ENDPOINT": "https://example.invalid",
    "S3_REGION": "auto",
    "S3_BUCKET": "bot-state",
    "S3_ACCESS_KEY_ID": "access-key",
    "S3_SECRET_ACCESS_KEY": "secret-key",
}


class JsonStateTest(unittest.TestCase):
    def test_local_backend_seeds_and_round_trips_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "state.json"
            with patch.dict(os.environ, {"BOT_STATE_BACKEND": "local"}, clear=True):
                state = JsonState(str(path), "state.json")
                self.assertEqual(state.load(), {})
                state.save({"answer": 42})
                self.assertEqual(state.load(), {"answer": 42})

    def test_s3_backend_requires_all_connection_settings(self) -> None:
        with patch.dict(os.environ, {"BOT_STATE_BACKEND": "s3"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "S3_ENDPOINT"):
                JsonState("unused.json", "state.json")

    def test_s3_key_uses_normalized_prefix(self) -> None:
        with patch.dict(os.environ, S3_ENV, clear=True):
            state = JsonState("unused.json", "users.json")
        self.assertEqual(state.key, "bots/solid-funicular/users.json")

    def test_missing_s3_object_is_initialized(self) -> None:
        missing = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "missing"}},
            "GetObject",
        )
        client = Mock()
        client.get_object.side_effect = missing
        with patch.dict(os.environ, S3_ENV, clear=True):
            state = JsonState("unused.json", "users.json")
            state._client = client
            self.assertEqual(state.load(), {})
        client.put_object.assert_called_once_with(
            Bucket="bot-state",
            Key="bots/solid-funicular/users.json",
            Body=b"{}",
            ContentType="application/json",
        )

    def test_s3_object_round_trips_json(self) -> None:
        client = Mock()
        client.get_object.return_value = {"Body": io.BytesIO(b'{"answer": 42}')}
        with patch.dict(os.environ, S3_ENV, clear=True):
            state = JsonState("unused.json", "users.json")
            state._client = client
            self.assertEqual(state.load(), {"answer": 42})

    def test_non_missing_s3_error_is_not_hidden(self) -> None:
        denied = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "denied"}},
            "GetObject",
        )
        client = Mock()
        client.get_object.side_effect = denied
        with patch.dict(os.environ, S3_ENV, clear=True):
            state = JsonState("unused.json", "users.json")
            state._client = client
            with self.assertRaises(ClientError):
                state.load()


if __name__ == "__main__":
    unittest.main()
