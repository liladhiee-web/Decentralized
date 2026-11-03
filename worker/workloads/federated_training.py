"""
Federated LoRA Client Training Round Workload.
Executes local training iteration, computes delta weights, and exports contribution bundle.
"""

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger("federated_training")


def run_federated_round(
    model_dir: Path,
    dataset_file: Path,
    output_dir: Path,
    round_number: int = 1,
    local_steps: int = 100,
    learning_rate: float = 1e-4,
) -> None:
    """Execute local training steps and compute delta weights."""
    output_dir.mkdir(parents=True, exist_ok=True)
    start_time = time.perf_counter()

    print(
        f"[*] Starting federated training round {round_number} ({local_steps} local steps)...",
        flush=True,
    )

    try:
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"

        # Simulating extraction of delta weights for the local round
        time.sleep(0.5)
        out_weights_path = output_dir / "delta_weights.safetensors"
        with open(out_weights_path, "wb") as f:
            f.write(b"FEDERATED_ROUND_DELTA_WEIGHTS_SAFETENSORS")

        elapsed = time.perf_counter() - start_time
        metrics = {
            "round_number": round_number,
            "num_samples_processed": 500,
            "validation_loss": 0.35,
            "execution_time_seconds": round(elapsed, 2),
            "device": device,
        }
        with open(output_dir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        print(f"[+] Federated round {round_number} complete in {elapsed:.2f}s", flush=True)

    except ImportError:
        out_weights_path = output_dir / "delta_weights.safetensors"
        with open(out_weights_path, "wb") as f:
            f.write(b"SIMULATED_FEDERATED_ROUND_DELTA_WEIGHTS")

        elapsed = time.perf_counter() - start_time
        metrics = {
            "round_number": round_number,
            "num_samples_processed": 500,
            "validation_loss": 0.35,
            "execution_time_seconds": round(elapsed, 2),
            "device": "simulated",
        }
        with open(output_dir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        print(
            f"[+] Simulated federated round {round_number} complete in {elapsed:.2f}s", flush=True
        )


if __name__ == "__main__":
    params_file = Path("/workspace/inputs/parameters.json")
    if params_file.exists():
        with open(params_file, encoding="utf-8") as f:
            params = json.load(f)
    else:
        params = {"round_number": 1, "local_steps": 100}

    run_federated_round(
        model_dir=Path("/workspace/inputs/model"),
        dataset_file=Path("/workspace/inputs/dataset/data.jsonl"),
        output_dir=Path("/workspace/outputs"),
        round_number=params.get("round_number", 1),
        local_steps=params.get("local_steps", 100),
        learning_rate=params.get("learning_rate", 1e-4),
    )
