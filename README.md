# GitRoot:1 — VulnHub Walkthrough

Full exploitation of the VulnHub box [**GitRoot:1**](https://www.vulnhub.com/entry/gitroot-1,488/), from recon to root, with both flags captured.

- [`writeup.md`](writeup.md) — full command/output record, reproducible step by step
- [`slides.md`](slides.md) — presentation draft (one H2 per slide)
- [`scripts/`](scripts/) — the exploit code used in the chain

## Attack path

| Step | Technique |
|------|-----------|
| Recon | `nmap` → SSH (22), Apache (80), memcached (11211) |
| Web | vhost enumeration → `repo.gitroot.vuln` with exposed `/.git` |
| Creds | GitTools `/.git` dump → memcached SASL creds in git history |
| memcached | SASL binary dump → SHA1 hashes → rockyou → **pablo** |
| pablo → beth | password recovered from a `/opt/auth` git history blob |
| beth → jen | 7z archive drops a `post-commit` hook into jen's cron repo; `.viminfo` leaks jen's password |
| jen → root | `sudo git` (GTFOBins) |

## Scripts

| File | Purpose |
|------|---------|
| `scripts/memcached_dump.py` | SASL binary-protocol dump of the three password-hash keys |
| `scripts/crack_sha1.py` | Crack the raw-SHA1 hashes against rockyou |
| `scripts/beth_to_jen_7z.sh` | Build + drop the malicious 7z `post-commit` hook (run as beth) |
| `scripts/jen_to_root.sh` | `sudo git` → root via `core.editor` (run as jen) |

## Disclaimer

For educational use against a deliberately vulnerable lab VM in an authorized,
isolated environment only. Do not use against systems you do not own or have
explicit permission to test.
