# solid-funicular

Discord bot state is stored either in local JSON files or an S3-compatible
object store. Production uses Cloudflare R2 with the same environment contract
as CodeRunBot:

- `BOT_STATE_BACKEND=s3`
- `BOT_STATE_PREFIX=bots/solid-funicular`
- `S3_ENDPOINT`, `S3_REGION`, `S3_BUCKET`
- `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`

Missing objects are initialized as empty JSON documents. A missing bucket or
an authorization failure remains fatal instead of silently discarding state.

Run the tests with `uv run python -m unittest discover -s tests -v`.
Pushes to `main` publish multi-architecture images to GHCR as `latest` and
`sha-<commit>`.
