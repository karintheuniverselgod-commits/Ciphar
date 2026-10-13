#!/usr/bin/env bash
# Step 1: installs Python + the libraries inside this folder.  Run:  bash install.sh
set -e
cd "$(dirname "$0")"
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
./venv/bin/python -c "import poster; poster.ensure_fonts(); print('fonts ready')"
echo
echo "Done. Now open .env, paste your bot token, then run:  bash install_service.sh"
