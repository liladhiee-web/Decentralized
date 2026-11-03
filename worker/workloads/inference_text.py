"""
Text Generation Workload Runner (Hugging Face Transformers / Safetensors).
Executes inside the sandboxed Docker container or in local simulation mode.
"""

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger("inference_text")


def run_text_inference(
    model_dir: Path,
    output_dir: Path,
    prompt: str,
    max_tokens: int = 256,
    temperature: float = 0.7,
    top_p: float = 0.9,
) -> None:
    """Execute text generation against local Safetensors model weights."""
    output_dir.mkdir(parents=True, exist_ok=True)
    start_time = time.perf_counter()

    print(f"[*] Initializing model inference for prompt ({len(prompt)} chars)...", flush=True)

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[*] Target compute device: {device}", flush=True)

        tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        model = AutoModelForCausalLM.from_pretrained(
            str(model_dir),
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map="auto" if device == "cuda" else None,
        )

        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        print("[*] Generating tokens...", flush=True)

        with torch.no_grad():
            output_tokens = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=temperature > 0.0,
            )

        output_text = tokenizer.decode(output_tokens[0], skip_special_tokens=True)
        tokens_generated = len(output_tokens[0]) - inputs.input_ids.shape[1]
        elapsed = time.perf_counter() - start_time
        tokens_per_sec = round(tokens_generated / max(0.001, elapsed), 2)

        # Write output text
        with open(output_dir / "output.txt", "w", encoding="utf-8") as f:
            f.write(output_text)

        # Write metrics
        metrics = {
            "tokens_generated": tokens_generated,
            "execution_time_seconds": round(elapsed, 2),
            "tokens_per_second": tokens_per_sec,
            "device": device,
        }
        with open(output_dir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        print(
            f"[+] Generation complete: {tokens_generated} tokens in {elapsed:.2f}s ({tokens_per_sec} t/s)",
            flush=True,
        )

    except ImportError:
        # Fallback simulated runner when torch is not installed in the environment
        print(
            "[*] PyTorch not available in execution environment; running simulated generation...",
            flush=True,
        )
        time.sleep(0.5)
        simulated_output = (
            f"[AI Cloud Output]: Response to prompt: '{prompt[:50]}...' generated successfully."
        )
        elapsed = time.perf_counter() - start_time

        with open(output_dir / "output.txt", "w", encoding="utf-8") as f:
            f.write(simulated_output)

        with open(output_dir / "output.safetensors", "wb") as f:
            f.write(b"MOCK_GENERATION_TENSORS")

        metrics = {
            "tokens_generated": max_tokens,
            "execution_time_seconds": round(elapsed, 2),
            "tokens_per_second": 45.0,
            "device": "simulated",
        }
        with open(output_dir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        print(f"[+] Simulated generation completed in {elapsed:.2f}s", flush=True)


if __name__ == "__main__":
    params_file = Path("/workspace/inputs/parameters.json")
    if params_file.exists():
        with open(params_file, encoding="utf-8") as f:
            params = json.load(f)
    else:
        params = {"prompt": "Hello world", "max_tokens": 128}

    run_text_inference(
        model_dir=Path("/workspace/inputs/model"),
        output_dir=Path("/workspace/outputs"),
        prompt=params.get("prompt", "Hello world"),
        max_tokens=params.get("max_tokens", 256),
        temperature=params.get("temperature", 0.7),
        top_p=params.get("top_p", 0.9),
    )
