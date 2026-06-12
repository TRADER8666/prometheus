#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS=("llama3.2:3b" "qwen2.5-coder:1.5b" "nomic-embed-text" "llava")

# Host-side venv is used for installer utilities on Ubuntu 24.04+ (PEP 668).
VENV_DIR="/opt/prometheus/venv"
VENV_BIN="${VENV_DIR}/bin"
VENV_PYTHON="${VENV_BIN}/python"
VENV_PIP="${VENV_BIN}/pip"

# If set to 1, install full backend requirements on host as well.
# Default keeps host Python footprint smaller since backend runs in Docker.
INSTALL_HOST_FULL_PYTHON="${INSTALL_HOST_FULL_PYTHON:-0}"

# Set to 1 when user is freshly added to docker group (no re-login needed)
DOCKER_GROUP_FRESH=0

log() { echo "[prometheus-install] $*"; }
need_sudo() { if [[ $EUID -ne 0 ]]; then echo "sudo"; fi; }
SUDO="$(need_sudo)"
INSTALL_USER="${SUDO_USER:-$USER}"

require_debian() {
  if [[ ! -f /etc/debian_version ]]; then
    echo "This installer currently supports Ubuntu/Debian only."
    exit 1
  fi
}

preflight_checks() {
  # Pre-flight checks
  echo "Running pre-flight checks..."

  # Check if user is in docker group (if docker is already installed)
  if command -v docker &> /dev/null; then
    if ! groups | grep -q docker; then
      echo "ℹ️  You are not in the 'docker' group yet. The script will handle this automatically."
    fi
  fi

  # Check for write permissions to /opt
  if [ ! -w "/opt" ] && [ ! -d "/opt/prometheus" ]; then
    echo "Will need sudo to create /opt/prometheus"
  fi

  echo "✓ Pre-flight checks complete"
  echo ""
}

install_base_packages() {
  log "Installing base packages..."
  $SUDO apt-get update
  $SUDO apt-get install -y \
    ca-certificates curl gnupg lsb-release software-properties-common \
    apt-transport-https net-tools ufw git jq rsync unzip \
    pciutils python3 python3-pip python3-venv ffmpeg \
    libgl1 libglib2.0-0 libsndfile1 portaudio19-dev
}

setup_python_venv() {
  # Create virtual environment
  if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment at $VENV_DIR..."
    $SUDO mkdir -p /opt/prometheus
    $SUDO python3 -m venv "$VENV_DIR"
    # Ensure current user owns the entire /opt/prometheus directory
    $SUDO chown -R "$INSTALL_USER":"$INSTALL_USER" /opt/prometheus
    echo "✓ Virtual environment created and permissions set"
  fi

  # Verify permissions
  if [ ! -w "/opt/prometheus" ]; then
    echo "⚠️  Warning: /opt/prometheus is not writable by current user"
    echo "Attempting to fix permissions..."
    $SUDO chown -R "$INSTALL_USER":"$INSTALL_USER" /opt/prometheus
  fi

  if [[ ! -x "$VENV_PYTHON" || ! -x "$VENV_PIP" ]]; then
    echo "Virtual environment is missing python/pip binaries at $VENV_DIR"
    exit 1
  fi

  export PATH="$VENV_BIN:$PATH"
  log "Using installer Python from venv: $VENV_PYTHON"
}

install_docker() {
  if command -v docker >/dev/null 2>&1; then
    log "Docker already installed."
  else
    log "Installing Docker..."
    $SUDO install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | $SUDO gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    $SUDO chmod a+r /etc/apt/keyrings/docker.gpg
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      $SUDO tee /etc/apt/sources.list.d/docker.list > /dev/null
    $SUDO apt-get update
    $SUDO apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    $SUDO usermod -aG docker "$INSTALL_USER" || true
  fi

  if ! docker compose version >/dev/null 2>&1; then
    log "Docker Compose plugin missing, installing docker-compose package fallback..."
    $SUDO apt-get install -y docker-compose
  fi

  # Track if user was just added to docker group (needed later for sg docker)
  if ! groups | grep -q docker; then
    DOCKER_GROUP_FRESH=1
    log "You were just added to the 'docker' group. Will use 'sg docker' for container commands."
  else
    DOCKER_GROUP_FRESH=0
  fi
}

setup_nvidia_or_amd() {
  if lspci | grep -Eiq 'NVIDIA'; then
    log "NVIDIA GPU detected. Installing NVIDIA driver + CUDA toolkit."
    $SUDO apt-get install -y ubuntu-drivers-common
    $SUDO ubuntu-drivers autoinstall || true
    $SUDO apt-get install -y nvidia-cuda-toolkit || true
  elif lspci | grep -Eiq 'AMD/ATI'; then
    log "AMD GPU detected. Installing Mesa/OpenCL stack."
    $SUDO apt-get install -y mesa-opencl-icd clinfo || true
  else
    log "No dedicated NVIDIA/AMD GPU detected. CPU mode will be used."
  fi
}

install_python_ai_deps() {
  log "Installing host-side Python tooling in venv (Ubuntu 24.04 compatible)..."
  "$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel

  # Torch first so whisper/vision packages resolve efficiently.
  if command -v nvidia-smi >/dev/null 2>&1; then
    "$VENV_PIP" install torch torchvision --extra-index-url https://download.pytorch.org/whl/cu121 || \
      "$VENV_PIP" install torch torchvision --index-url https://download.pytorch.org/whl/cpu || true
  else
    "$VENV_PIP" install torch torchvision --index-url https://download.pytorch.org/whl/cpu || \
      "$VENV_PIP" install torch torchvision || true
  fi

  if [[ "$INSTALL_HOST_FULL_PYTHON" == "1" ]]; then
    log "INSTALL_HOST_FULL_PYTHON=1 -> installing full backend requirements on host venv"
    "$VENV_PIP" install -r "$PROJECT_DIR/backend/requirements.txt" || true
  else
    log "Installing only installer utility packages on host (backend runtime stays in Docker containers)"
    "$VENV_PIP" install \
      ultralytics diffusers transformers accelerate easyocr \
      openai-whisper piper-tts playwright Pillow opencv-python numpy \
      APScheduler croniter webrtcvad soundfile || true
  fi

  log "Installing Playwright Chromium browser..."
  "$VENV_PYTHON" -m playwright install chromium || true

  log "Preloading Whisper small model..."
  "$VENV_PYTHON" - << 'PY'
import whisper
whisper.load_model('small')
print('Whisper small ready')
PY

  log "Downloading/caching YOLO model weights (yolov8n.pt)..."
  "$VENV_PYTHON" - << 'PY'
from ultralytics import YOLO
YOLO('yolov8n.pt')
print('YOLO weights ready')
PY
}

install_piper_voice() {
  log "Installing piper-tts assets..."
  $SUDO mkdir -p /opt/prometheus/voices
  if [ ! -f /opt/prometheus/voices/en_US-lessac-medium.onnx ]; then
    curl -L -o /tmp/en_US-lessac-medium.onnx \
      https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx || true
    curl -L -o /tmp/en_US-lessac-medium.onnx.json \
      https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json || true
    $SUDO mv /tmp/en_US-lessac-medium.onnx /opt/prometheus/voices/en_US-lessac-medium.onnx 2>/dev/null || true
    $SUDO mv /tmp/en_US-lessac-medium.onnx.json /opt/prometheus/voices/en_US-lessac-medium.onnx.json 2>/dev/null || true
  fi
}

install_ollama_native() {
  if command -v ollama >/dev/null 2>&1; then
    log "Ollama already installed."
  else
    log "Installing Ollama (native host service)..."
    curl -fsSL https://ollama.com/install.sh | sh
  fi

  $SUDO systemctl enable ollama || true
  $SUDO systemctl restart ollama || true

  log "Waiting for Ollama API..."
  for _ in $(seq 1 45); do
    if curl -sf http://127.0.0.1:11434/api/tags >/dev/null; then
      break
    fi
    sleep 1
  done

  for model in "${MODELS[@]}"; do
    log "Pulling model: $model"
    ollama pull "$model" || true
  done
}

prepare_app_dirs() {
  mkdir -p "$PROJECT_DIR"/{data,workspace,chroma_data,searxng}
  mkdir -p "$PROJECT_DIR/backend/workspace/images"
  mkdir -p "$PROJECT_DIR/backend/workspace/audio"
}

install_systemd_service() {
  log "Installing systemd service..."
  $SUDO mkdir -p /opt
  $SUDO rsync -a --delete "$PROJECT_DIR"/ /opt/prometheus/
  $SUDO cp /opt/prometheus/prometheus.service /etc/systemd/system/prometheus.service
  $SUDO systemctl daemon-reload
  $SUDO systemctl enable prometheus.service
}

configure_lan() {
  log "Configuring LAN accessibility and firewall..."
  $SUDO ufw allow 80/tcp || true
  $SUDO ufw allow 3000/tcp || true
  $SUDO ufw allow 8000/tcp || true
  $SUDO ufw allow 8080/tcp || true
  $SUDO ufw allow 11434/tcp || true

  $SUDO mkdir -p /etc/systemd/system/ollama.service.d
  cat << EOC | $SUDO tee /etc/systemd/system/ollama.service.d/override.conf >/dev/null
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOC
  $SUDO systemctl daemon-reload
  $SUDO systemctl restart ollama || true
}

docker_cmd() {
  # Run a docker/docker-compose command, using sg docker if group was just added
  if [[ "$DOCKER_GROUP_FRESH" -eq 1 ]]; then
    sg docker -c "$*"
  else
    eval "$@"
  fi
}

start_stack() {
  log "Starting Prometheus stack with Docker Compose..."
  cd /opt/prometheus
  docker_cmd "docker compose up -d --build"

  log "Services status:"
  docker_cmd "docker compose ps"

  LAN_IP=$(hostname -I | awk '{print $1}')
  log "Prometheus UI should be available at: http://${LAN_IP}"
  log "Backend API: http://${LAN_IP}/api"
}

main() {
  require_debian
  preflight_checks
  install_base_packages
  setup_python_venv
  install_docker
  setup_nvidia_or_amd
  install_python_ai_deps
  install_piper_voice
  install_ollama_native
  prepare_app_dirs
  install_systemd_service
  configure_lan
  start_stack
  log "✅ Install complete! Prometheus is running."
  log "To update later, run: ./update.sh"
}

main "$@"
