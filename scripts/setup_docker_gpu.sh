#!/usr/bin/env bash
# Install Docker Engine + NVIDIA runtime on Ubuntu, then build and start VN_ID.
# Sources: https://docs.docker.com/engine/install/ubuntu/
# https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source /etc/os-release
if [[ "$ID" != ubuntu ]]; then
    echo "This installer supports Ubuntu only." >&2
    exit 1
fi
if [[ "$(ps -p 1 -o comm=)" != systemd ]]; then
    echo "Enable systemd in WSL before running this installer." >&2
    exit 1
fi
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi
else
    /usr/lib/wsl/lib/nvidia-smi
fi
if (( EUID != 0 )); then
    exec sudo -- bash "$PWD/scripts/setup_docker_gpu.sh"
fi

apt-get update
apt-get install -y --no-install-recommends ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings

if ! command -v docker >/dev/null 2>&1; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
docker compose version
docker buildx version

if ! command -v nvidia-ctk >/dev/null 2>&1; then
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
        | gpg --dearmor --yes -o /etc/apt/keyrings/nvidia-container-toolkit.gpg
    curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
        | sed 's#deb https://#deb [signed-by=/etc/apt/keyrings/nvidia-container-toolkit.gpg] https://#g' \
        > /etc/apt/sources.list.d/nvidia-container-toolkit.list
    apt-get update
    apt-get install -y nvidia-container-toolkit
fi
# WSL uses the Windows NVIDIA driver; do not install a Linux display driver.
nvidia-ctk runtime configure --runtime=docker
systemctl enable --now docker
systemctl restart docker
docker info >/dev/null

docker compose config --quiet
docker compose build
# Verify real CUDA execution and the operator used by DBNet before starting API.
docker compose run --rm --no-deps -T vn-id python - <<'PY'
import torch
from torchvision.ops import deform_conv2d

assert torch.cuda.is_available(), "NVIDIA GPU is not available to the container"
x = torch.randn(1, 1, 5, 5, device="cuda")
w = torch.randn(1, 1, 3, 3, device="cuda")
offset = torch.zeros(1, 18, 3, 3, device="cuda")
assert deform_conv2d(x, offset, w).shape == (1, 1, 3, 3)
torch.cuda.synchronize()
print("CUDA OK:", torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0))
PY
docker compose up -d --wait --wait-timeout 120
docker compose exec -T vn-id python - <<'PY'
import json
from urllib.request import urlopen

with urlopen("http://127.0.0.1:8000/health", timeout=10) as response:
    health = json.load(response)
assert health["device"] == "cuda", health
print(health)
PY
echo "VN_ID GPU is running: http://127.0.0.1:8000/docs"
echo "OCR models load on the first image request; CUDA/health checks do not test OCR accuracy."
