# thumbnail-creation

## Known limitations

- `docker-compose.yml` (the `api` + `worker` + `postgres` multi-container setup) has not been run end to end in this development environment, since Docker was not available here. The individual pieces have been verified separately (the app boots via `uvicorn`, the worker runs via `python -m app.worker`, both against a real local Postgres instance), but the compose file's networking, build, and shared volume between `api` and `worker` have not been confirmed to work together. Please run `docker compose up --build` yourself to verify before relying on it.
