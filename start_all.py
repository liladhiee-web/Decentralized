#!/usr/bin/env python3
"""
Decentralized AI Cloud Platform - All-in-One Service & Tunnel Orchestrator.
Starts:
1. FastAPI Coordinator Server (:8000)
2. Next.js Web Dashboard (:3000)
3. Cloudflare Tunnel for Dashboard
4. Cloudflare Tunnel for Coordinator & WebSockets
Captures and prints the live public HTTPS/WSS URLs automatically.
"""

import atexit
import functools
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from threading import Thread
from typing import TextIO

# Ensure instant unbuffered output even when redirected to files or pipes
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True)
print = functools.partial(print, flush=True)

PROJECT_ROOT = Path(__file__).resolve().parent
CLOUDFLARED = PROJECT_ROOT / "tools" / "cloudflared.exe"
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"

processes: list[subprocess.Popen] = []


def kill_process_on_port(port: int) -> None:
    """Kill any existing process listening on the given port (Windows)."""
    try:
        cmd = f'powershell -Command "Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique"'
        out = subprocess.check_output(cmd, shell=True, text=True).strip()
        for pid_str in out.splitlines():
            pid_str = pid_str.strip()
            if pid_str and pid_str != "0":
                pid = int(pid_str)
                print(f"[*] Port {port} is occupied by PID {pid}. Freeing port...")
                subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
                time.sleep(0.5)
    except Exception:
        pass


def kill_existing_cloudflared() -> None:
    """Terminate any lingering cloudflared tunnel processes."""
    try:
        subprocess.run("taskkill /F /IM cloudflared.exe", shell=True, capture_output=True)
    except Exception:
        pass


def cleanup() -> None:
    """Terminate all spawned child processes cleanly."""
    print("\n[*] Shutting down all tunnels and local servers...")
    for p in processes:
        if p.poll() is None:
            try:
                p.terminate()
                p.kill()
            except Exception:
                pass
    kill_existing_cloudflared()
    kill_process_on_port(8000)
    kill_process_on_port(3000)
    print("[+] All services stopped.")


atexit.register(cleanup)


def signal_handler(sig, frame) -> None:
    cleanup()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def capture_tunnel_url(pipe: TextIO, url_holder: list[str], name: str = "Tunnel") -> None:
    """Thread target that parses Cloudflare output to capture the public URL."""
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
    while True:
        line = pipe.readline()
        if not line:
            break
        match = url_pattern.search(line)
        if match and not url_holder:
            found_url = match.group(0)
            url_holder.append(found_url)
            print(f"[+] {name} established: {found_url}")


def main() -> None:
    print("=" * 80)
    print("🚀 STARTING DECENTRALIZED AI CLOUD PLATFORM + CLOUDFLARE TUNNELS")
    print("=" * 80)

    if not CLOUDFLARED.exists():
        print(f"[!] Error: cloudflared not found at {CLOUDFLARED}")
        sys.exit(1)

    # 1. Ensure SQLite tables exist before starting
    print("[*] Verifying database schema...")
    try:
        import asyncio

        import coordinator.models  # noqa: F401
        from coordinator.database import Base, engine

        async def init_db():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        asyncio.run(init_db())
        print("[+] Database schema verified.")
    except Exception as e:
        print(f"[!] Database warning: {e}")

    # 2. Free ports and old tunnels if occupied
    kill_existing_cloudflared()
    kill_process_on_port(8000)
    kill_process_on_port(3000)

    # 3. Start Coordinator Server on :8000
    print("[*] Launching Coordinator Server on http://localhost:8000...")
    coord_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "coordinator.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]
    coord_proc = subprocess.Popen(coord_cmd, cwd=str(PROJECT_ROOT))
    processes.append(coord_proc)

    # 4. Start Next.js Dashboard on :3000
    print("[*] Launching Next.js Web Dashboard on http://localhost:3000...")
    dash_proc = subprocess.Popen(
        "npm run dev",
        shell=True,
        cwd=str(DASHBOARD_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    processes.append(dash_proc)

    # Give servers 2 seconds to initialize ports
    time.sleep(2.5)

    # 5. Start Cloudflare Tunnel for Dashboard (:3000)
    print("[*] Creating Cloudflare Tunnel for Web Dashboard (port 3000)...")
    dash_tunnel_cmd = [str(CLOUDFLARED), "tunnel", "--url", "http://localhost:3000"]
    dash_tunnel_proc = subprocess.Popen(
        dash_tunnel_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    processes.append(dash_tunnel_proc)

    dash_url_holder: list[str] = []
    dash_thread = Thread(
        target=capture_tunnel_url,
        args=(dash_tunnel_proc.stdout, dash_url_holder, "Web Dashboard Tunnel"),
        daemon=True,
    )
    dash_thread.start()

    # 6. Start Cloudflare Tunnel for Coordinator API (:8000)
    print("[*] Creating Cloudflare Tunnel for Coordinator & WebSockets (port 8000)...")
    coord_tunnel_cmd = [str(CLOUDFLARED), "tunnel", "--url", "http://localhost:8000"]
    coord_tunnel_proc = subprocess.Popen(
        coord_tunnel_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    processes.append(coord_tunnel_proc)

    coord_url_holder: list[str] = []
    coord_thread = Thread(
        target=capture_tunnel_url,
        args=(coord_tunnel_proc.stdout, coord_url_holder, "Coordinator API Tunnel"),
        daemon=True,
    )
    coord_thread.start()

    # Wait for both tunnel URLs to be captured (max 25s)
    print("[*] Waiting for Cloudflare to allocate secure tunnels...")
    start_wait = time.time()
    while time.time() - start_wait < 25:
        if dash_url_holder and coord_url_holder:
            break
        time.sleep(0.5)

    dash_url = dash_url_holder[0] if dash_url_holder else "http://localhost:3000 (Tunnel pending)"
    coord_url = (
        coord_url_holder[0] if coord_url_holder else "http://localhost:8000 (Tunnel pending)"
    )
    ws_url = coord_url.replace("https://", "wss://").replace("http://", "ws://") + "/ws/workers"

    print("\n" + "=" * 80)
    print("🎉 ALL PLATFORM SERVICES & SECURE TUNNELS ARE LIVE!")
    print("=" * 80)
    print(f"🌐 Web Dashboard (Public):   {dash_url}")
    print(f"📊 Marketplace Page:        {dash_url}/marketplace")
    print(f"⚙️ Coordinator API (Public):  {coord_url}")
    print(f"📖 Swagger Docs:             {coord_url}/docs")
    print(f"🔌 WebSocket Gateway:        {ws_url}")
    print("-" * 80)
    print("🔑 KAGGLE / COLAB WORKER CODE SNIPPET (Copy & Paste into Notebook):")
    print(f"""
import os
os.environ["COORDINATOR_URL"] = "{coord_url}"
os.environ["WORKER_ID"] = "d3c69c88-4d2d-4675-b2f7-3285ddaed518"
os.environ["WORKER_TOKEN"] = "Tyhb0yvipG_Kkz4CKGNSw1jBBWTS0gfrNZ9a6aIUbWM"
os.environ["WORKER_NAME"] = "kaggle-dual-t4"

from worker.agent import WorkerAgent
agent = WorkerAgent()
await agent.run()
""")
    print("=" * 80)
    print("[*] Press Ctrl+C anytime to stop all servers and tunnels cleanly.\n")

    # Keep script alive
    try:
        while True:
            time.sleep(1)
            # Check if any crucial process died
            if coord_proc.poll() is not None:
                print("[!] Coordinator process terminated unexpectedly.")
                break
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
