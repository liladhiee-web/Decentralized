#!/usr/bin/env python3
"""
Decentralized AI Cloud - Kaggle GPU Compute Provider Daemon.
Runs inside a free Kaggle Notebook with NVIDIA T4 or P100 GPU and connects
to the Coordinator over Cloudflare Tunnel WebSockets.
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from worker.agent import WorkerAgent

if __name__ == "__main__":
    print("[*] Starting Decentralized AI Cloud Worker on Kaggle...")
    agent = WorkerAgent()
    try:
        import asyncio
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        print("[*] Worker stopped by user.")

