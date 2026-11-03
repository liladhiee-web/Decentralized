# Community GPU Worker Onboarding & Operations Runbook

This runbook guides community compute providers through setting up, registering, and running an untrusted GPU worker node connected to the CloudAI Coordinator.

---

## 1. System & Hardware Prerequisites

### Host System Requirements

- **Operating System:** Ubuntu 22.04 LTS / 24.04 LTS or Debian 12 (x86_64 or aarch64)
- **Processor:** 4+ physical CPU cores
- **Memory:** 16 GB+ System RAM
- **Storage:** 100 GB+ free NVMe or SSD space for caching model weights and checkpoints
- **Networking:** Outbound HTTPS/WSS internet connectivity (`443`). **No public IP, domain, or port-forwarding required.**

### GPU & Driver Requirements

- **Hardware:** NVIDIA GPU (Ampere, Ada Lovelace, Hopper, Blackwell, or Turing: RTX 3090, RTX 4090, A10, A100, H100, L40S, etc.)
- **NVIDIA Proprietary Driver:** Version 535.xx or newer:
  ```bash
  nvidia-smi
  ```
- **NVIDIA Container Toolkit:** Configured in Docker Engine to expose GPUs to containers.
  ```bash
  # Check if nvidia runtime is configured
  docker info | grep -i "Runtimes:.*nvidia"
  ```

---

## 2. Setting Up NVIDIA Container Toolkit (One-Time Setup)

If NVIDIA Container Toolkit is not yet installed:

```bash
# 1. Configure the repository
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# 2. Install the toolkit packages
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit

# 3. Configure Docker daemon to use NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# 4. Verify GPU access inside test container
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

---

## 3. Worker Registration

Before starting the daemon, register the worker with the coordinator to obtain a **Worker Registration Token**.

### Using the CloudAI CLI:

```bash
# 1. Login with your provider credentials
cloudai auth login --email provider@example.com

# 2. Register a new worker node
cloudai workers register --name "node-rtx4090-alpha"
```

The output will display:
```text
Worker ID: 4b29f07a-2270-4d87-9bb3-2287c2f6d0f1
Registration Token: cld_wrk_7a8f9021e...
Status: active
```

Save this `WORKER_TOKEN` securely.

---

## 4. Automated Installation via `install.sh`

Run the installation script:

```bash
# Run installer specifying your coordinator URL and worker token
sudo bash deployment/install.sh \
  --token "cld_wrk_7a8f9021e..." \
  --coordinator "https://coordinator.cloudai.internal" \
  --dir "/opt/cloudai-worker"
```

The installer will:
1. Validate NVIDIA driver and Docker Container Toolkit presence.
2. Create dedicated isolated directory `/opt/cloudai-worker`.
3. Set up an isolated Python virtual environment with all required packages.
4. Copy the worker daemon and shared libraries.
5. Create configuration file `/opt/cloudai-worker/worker.conf`.
6. Install and enable the `cloudai-worker.service` systemd daemon.

---

## 5. Managing the Worker Daemon Service

The worker runs as a systemd background service.

### Starting and Stopping the Daemon:

```bash
# Start daemon
sudo systemctl start cloudai-worker

# Stop daemon
sudo systemctl stop cloudai-worker

# Restart daemon
sudo systemctl restart cloudai-worker

# Check service status
sudo systemctl status cloudai-worker
```

### Inspecting Live Logs:

```bash
# Stream daemon logs in real-time
journalctl -u cloudai-worker -f -n 50
```

### Verifying Connection in CloudAI CLI:

```bash
cloudai workers list
```

The worker status will display `ONLINE`, indicating that the persistent WebSocket connection is active and telemetry heartbeats are syncing every 15 seconds.

---

## 6. Troubleshooting Common Issues

### Issue 1: `NVML Shared Library Not Found` or `pynvml.NVMLError_LibraryNotFound`
- **Cause:** NVIDIA driver libraries are not in system dynamic linker path.
- **Resolution:**
  ```bash
  sudo ldconfig
  # Verify nvidia-smi runs without error
  nvidia-smi
  ```

### Issue 2: `DockerException: Error while fetching server API version`
- **Cause:** The user running the daemon does not have permission to communicate with `/var/run/docker.sock`.
- **Resolution:**
  ```bash
  sudo usermod -aG docker $USER
  newgrp docker
  ```

### Issue 3: `WebSocket Connection Refused (HTTP 401 / 403)`
- **Cause:** Invalid or revoked worker registration token.
- **Resolution:** Check `/opt/cloudai-worker/worker.conf` and verify `WORKER_TOKEN` matches the token in the coordinator database. Re-register if necessary.

### Issue 4: `CUDA Out of Memory (OOM) during Workload Execution`
- **Cause:** Model size or LoRA batch size exceeds available GPU VRAM.
- **Resolution:** The worker daemon automatically reports `TASK_FAILED` with error code `ERR_CUDA_OOM`. The coordinator scheduler will avoid dispatching oversized workloads to this GPU class in the future.
