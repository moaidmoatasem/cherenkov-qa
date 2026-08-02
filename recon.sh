#!/usr/bin/env bash
cd "$HOME/cherenkov-qa" || exit 1
export GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no -o IdentitiesOnly=yes -i /home/moaid/.ssh/id_ed25519_cherenkov -o ConnectTimeout=20"
echo "===push main via SSH==="
git push ssh://git@github.com:22/moaidmoatasem/cherenkov-qa.git main
echo "exit=$?"
echo "===verify via ls-remote==="
git ls-remote origin refs/heads/main
