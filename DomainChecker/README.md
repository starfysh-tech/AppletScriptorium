# DomainChecker

Local web tool that checks which TLDs are taken for a name. Type `mybrand`, get `.com`, `.io`, `.dev`, and the rest of the list in `tld_database.py`, each marked owned or free.

## Run

```bash
python3 -m pip install --user flask dnspython requests
python3 DomainChecker/domain_checker.py
# open http://127.0.0.1:5000
```

Options: `--host` (default `127.0.0.1`), `--port` (default `5000`), `--debug`.

## How a TLD is checked

Checks run in order and stop at the first hit (30 TLDs in parallel; 2s timeout for DNS and HTTP, 10s for whois):

1. **DNS** — A or NS record exists
2. **HTTP** — `HEAD` on https, then http, returns a status below 400 (redirects are not followed)
3. **WHOIS** — `whois` output contains registrar or creation-date fields

Each TLD gets one status:

- `taken` — a check hit
- `free` — no check hit and every lookup answered (HTTP errors count as no hit, since a free domain never answers HTTP)
- `unknown` — no check hit, but the DNS or whois lookup timed out or failed, so the TLD could not be judged

Free is a hint, not a guarantee. Confirm at a registrar before you buy.

## API

`POST /api/check` with `{"domain": "mybrand", "tlds": [".com", ".io"]}`. `tlds` is optional and defaults to every TLD in `tld_database.py`.

- `domain` must be a single label: letters, digits, hyphens, no leading or trailing hyphen. `mybrand.com` is rejected; send `mybrand`.
- TLDs not in `tld_database.py` are dropped. At most 500 are checked.
- Each result is `{"tld": ".com", "status": "taken" | "free" | "unknown", "method": "DNS" | "HTTP" | "WHOIS" | "FREE" | "UNKNOWN" | "ERROR"}`.

`GET /api/tlds` returns the TLD categories.

## Files

- `domain_checker.py` — Flask server, checker, and the UI (inline `HTML_TEMPLATE`)
- `tld_database.py` — TLD list grouped by theme

## Security

Keep the default `--host 127.0.0.1`. The server does not block domains that resolve to private IPs, so add that check before exposing it on a network.
