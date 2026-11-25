# GitRoot:1 — VulnHub Walkthrough

Target `192.168.122.243` · Attacker `192.168.122.1`
Two flags: `user.txt` (pablo) and `root.txt` (root)
Attack path: web `/.git` → memcached → SSH → beth → jen → root

## Lab setup

- `GitRoot.ova` verified (MD5 `0d7910629ab3b59fbd5c267d7152fd0a`)
- VirtualBox blocked by UEFI Secure Boot
- Ran under QEMU/KVM + libvirt NAT (DHCP); fixed guest NIC name to `enp0s3` via a systemd `.link`

## Recon

- `netdiscover` → target `192.168.122.243`
- `nmap -A -p-`:
  - 22 OpenSSH 7.9p1
  - 80 Apache 2.4.38 — title "Hey Jen"
  - 11211 memcached

## Web enumeration

- Index page leaks `wp.gitroot.vuln` → base domain `gitroot.vuln`
- `gobuster vhost` + `big.txt` → **`repo.gitroot.vuln`**
- `repo.gitroot.vuln`: "Code storage" app (`get.php`/`set.php` front memcached) with an exposed `/.git`

## Dump /.git → credentials in history

- `GitTools/gitdumper.sh` dumps the repo
- Recovered `get.php`/`set.php`/`stats.php` + a SHA256-named file listing memcached keys
- Git history still holds the real SASL creds:
  `setSaslAuthData("pablo@gitroot", "ihjedpvqfe")`

## memcached → SHA1 → crack pablo

- SASL (binary PLAIN) login; `cachedump` disabled, but key names came from git
- Keys `pablo_S3cret_P@ss` / `beth_S3cret_P@ss` / `jen_S3cret_P@ss` → SHA1 hashes
- rockyou cracks `pablo` SHA1 → **`mastergitar`**

## Foothold — user.txt

- `ssh pablo@target` with `mastergitar`
- `user.txt = 8a81007ea736a2b8a72a624672c375f9ac707b5e`

## pablo → beth (git history)

- `/opt/auth/.git` (beth) — `main.c` password check, sanitized to `"PASSWORD"`
- One historical blob keeps the real value: `strcmp(pass, "r3vpdmspqdb")`
- `ssh beth@target` → **beth : `r3vpdmspqdb`**

## beth → jen (7z → post-commit hook)

- jen cron every minute: extract `~jen/public/repos/*.7z` into a repo, `git add`, `git commit`
- Drop a 7z containing `.git/hooks/post-commit`; the commit runs it as **jen** ("Thanks beth!")
- Hook exfiltrates jen `.viminfo`; vim search history leaks **jen : `binzpbeocnexoe`**
- `PubkeyAuthentication no` → log in with the password

## jen → root (sudo git) — root.txt

- `sudo -l` → `(ALL) /usr/bin/git`
- GTFOBins: `sudo git -p help config` → `!/bin/sh` (here via `core.editor`) runs as root
- `root.txt = 734ae32be131cd0681f86c03858f4f587a3c69ce`

## Takeaways

- Never expose `/.git`; secrets in history are still secrets (rewrite, don't just "fix" the latest commit)
- Enforce memcached SASL *and* restrict access; sanitizing source ≠ rotating creds
- World-writable drop dirs + privileged cron that unpacks untrusted archives = code exec
- `.viminfo`/shell history leak secrets; never grant `sudo` on `git` (arbitrary code via hooks/pager/editor)
