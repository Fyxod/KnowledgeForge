#!/bin/bash

set -e

echo "========== Updating system =========="
sudo apt update && sudo apt upgrade -y

# ----------------------------
# Install MongoDB
# ----------------------------
echo "========== Installing MongoDB =========="
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo gpg --dearmor -o /usr/share/keyrings/mongodb-archive-keyring.gpg
echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-archive-keyring.gpg] https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt update
sudo apt install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod

# ----------------------------
# Install MongoDB Compass
# ----------------------------
echo "========== Installing MongoDB Compass =========="
wget https://downloads.mongodb.com/compass/mongodb-compass_1.41.1_amd64.deb -O /tmp/mongodb-compass.deb
sudo apt install -y /tmp/mongodb-compass.deb
rm /tmp/mongodb-compass.deb

# ----------------------------
# Install Node.js and npm
# ----------------------------
echo "========== Installing Node.js and npm =========="
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# ----------------------------
# Install Tesseract OCR
# ----------------------------
echo "========== Installing Tesseract OCR =========="
sudo apt install -y tesseract-ocr tesseract-ocr-eng

# ----------------------------
# Install pyenv
# ----------------------------
echo "========== Installing pyenv =========="
sudo apt install -y make build-essential libssl-dev zlib1g-dev \
libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev

curl https://pyenv.run | bash

# Add pyenv to shell
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# ----------------------------
# Install Python 3.11.8 via pyenv
# ----------------------------
echo "========== Installing Python 3.11.8 =========="
pyenv install -s 3.11.8
pyenv local 3.11.8

# ----------------------------
# Create virtual environment and install requirements
# ----------------------------
echo "========== Setting up Python virtual environment =========="
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi

# ----------------------------
# Run two Ollama instances
# ----------------------------
echo "========== Starting Ollama instances =========="
# Check and kill existing instances if any
pkill -f "ollama serve" || true

# First instance (port 11435, unlimited keep-alive)
OLLAMA_HOST=0.0.0.0:11435 OLLAMA_KEEP_ALIVE=-1 nohup ollama serve > ollama_11435.log 2>&1 &

# Second instance (port 11434, 3 minutes keep-alive)
OLLAMA_HOST=0.0.0.0:11434 OLLAMA_KEEP_ALIVE=3m nohup ollama serve > ollama_11434.log 2>&1 &

echo "Ollama servers started. Logs: ollama_11435.log, ollama_11434.log"

# ----------------------------
# Run custom script
# ----------------------------
if [ -f setmodel.sh ]; then
    echo "========== Running custom script =========="
    ./setmodel.sh
fi

echo "========== Setup complete! =========="
