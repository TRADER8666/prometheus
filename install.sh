#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODELS=("llama3.2:3b" "qwen2.5-coder:1.5b" "nomic-embed-text" "llava")

log() { echo "[prometheus-install] $*"; }
need_sudo() { if [[ $EUID -ne 0 ]]; then echo "sudo"; fi; }
SUDO="$(need_sudo)"

require_debian() {
  if [[ ! -f /etc/debian_version ]]; then
    echo "This installer currently supports Ubuntu/Debian only."
    exit 1
  fi
}

install_base_packages() {
  log "Installing base packages..."
  $SUDO apt-get update
  $SUDO apt-get install -y \
    ca-certificates curl gnupg lsb-release software-properties-common \
    apt-transport-https net-tools ufw git jq rsync unzip \
    python3 python3-pip python3-venv ffmpeg \
    libgl1 libglib2.0-0 libsndfile1 portaudio19-dev
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
    $SUDO usermod -aG docker "$USER" || true
  fi

  if ! docker compose version >/dev/null 2>&1; then
    log "Docker Compose plugin missing, installing docker-compose package fallback..."
    $SUDO apt-get install -y docker-compose
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
  log "Installing Python AI dependencies..."
  python3 -m pip install --upgrade pip || true

  if command -v nvidia-smi >/dev/null 2>&1; then
    python3 -m pip install torch torchvision --extra-index-url https://download.pytorch.org/whl/cu121 || true
  else
    python3 -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu || true
  fi

  python3 -m pip install -r "$PROJECT_DIR/backend/requirements.txt" || true

  log "Installing Playwright Chromium browser..."
  python3 -m playwright install chromium || true

  log "Preloading Whisper small model..."
  python3 - << 'PY'
import whisper
whisper.load_model('small')
print('Whisper small ready')
PY

  log "Downloading/caching YOLO model weights (yolov8n.pt)..."
  python3 - << 'PY'
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

start_stack() {
  log "Starting Prometheus stack with Docker Compose..."
  cd /opt/prometheus
  docker compose up -d --build

  log "Services status:"
  docker compose ps

  LAN_IP=$(hostname -I | awk '{print $1}')
  log "Prometheus UI should be available at: http://${LAN_IP}"
  log "Backend API: http://${LAN_IP}/api"
}

main() {
  require_debian
  install_base_packages
  install_docker
  setup_nvidia_or_amd
  install_python_ai_deps
  install_piper_voice
  install_ollama_native
  prepare_app_dirs
  install_systemd_service
  configure_lan
  start_stack
  log "Install complete. If docker group was newly applied, re-login may be required."
}

main "$@"
