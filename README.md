# TA-pushover

Splunk app that sends notifications through the [Pushover.net](https://pushover.net/) API via:
- Alert action: `sendalert pushover`
- Custom search command: `pushover_send`

## Build

```shell
./ucc-build.sh
```

This generates:
- `output/TA-pushover/` (built app directory)
- `TA-pushover.spl` (installable app package)

## Test

Fast local test suite:

```shell
uv run pytest
```

Optional end-to-end smoke test against a local Splunk container:

```shell
docker compose up -d
uv run python app_test.py --send
```

`app_test.py` expects `~/.config/ta-pushover.json` for Splunk + Pushover credentials.
