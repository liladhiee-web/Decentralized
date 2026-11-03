"""
Image Generation Workload Runner (Diffusers / Stable Diffusion).
Executes diffusion sampling steps inside sandboxed container.
"""

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger("inference_image")


def run_image_inference(
    model_dir: Path,
    output_dir: Path,
    prompt: str,
    negative_prompt: str | None = None,
    width: int = 1024,
    height: int = 1024,
    num_inference_steps: int = 30,
    guidance_scale: float = 7.5,
    seed: int | None = None,
) -> None:
    """Execute diffusion pipeline to generate image artifact."""
    output_dir.mkdir(parents=True, exist_ok=True)
    start_time = time.perf_counter()

    print(
        f"[*] Starting image synthesis: '{prompt[:48]}...' ({width}x{height}, {num_inference_steps} steps)",
        flush=True,
    )

    try:
        import torch
        from diffusers import AutoPipelineForText2Image

        device = "cuda" if torch.cuda.is_available() else "cpu"
        generator = torch.Generator(device=device).manual_seed(seed) if seed else None

        pipe = AutoPipelineForText2Image.from_pretrained(
            str(model_dir),
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            variant="fp16" if device == "cuda" else None,
        ).to(device)

        def step_callback(pipe, step_index, timestep, callback_kwargs):
            pct = round((step_index + 1) / num_inference_steps * 100.0, 1)
            print(f"[*] Diffusion step {step_index + 1}/{num_inference_steps} ({pct}%)", flush=True)
            return callback_kwargs

        image = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            generator=generator,
            callback_on_step_end=step_callback,
        ).images[0]

        out_img_path = output_dir / "output.png"
        image.save(out_img_path)
        elapsed = time.perf_counter() - start_time

        metrics = {
            "width": width,
            "height": height,
            "num_inference_steps": num_inference_steps,
            "execution_time_seconds": round(elapsed, 2),
            "device": device,
        }
        with open(output_dir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        print(f"[+] Image generated successfully in {elapsed:.2f}s", flush=True)

    except ImportError:
        print(
            "[*] Diffusers/torch not installed; executing synthetic image generation...", flush=True
        )
        time.sleep(0.5)
        # Create a dummy valid PNG file or synthetic placeholder
        out_img_path = output_dir / "output.png"
        with open(out_img_path, "wb") as f:
            f.write(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01\x00\x00\x00\x01\x00\x08\x06\x00\x00\x00"
            )

        elapsed = time.perf_counter() - start_time
        metrics = {
            "width": width,
            "height": height,
            "num_inference_steps": num_inference_steps,
            "execution_time_seconds": round(elapsed, 2),
            "device": "simulated",
        }
        with open(output_dir / "metrics.json", "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)

        print(f"[+] Simulated image generation complete in {elapsed:.2f}s", flush=True)


if __name__ == "__main__":
    params_file = Path("/workspace/inputs/parameters.json")
    if params_file.exists():
        with open(params_file, encoding="utf-8") as f:
            params = json.load(f)
    else:
        params = {"prompt": "Futuristic skyline"}

    run_image_inference(
        model_dir=Path("/workspace/inputs/model"),
        output_dir=Path("/workspace/outputs"),
        prompt=params.get("prompt", "Futuristic skyline"),
        negative_prompt=params.get("negative_prompt"),
        width=params.get("width", 1024),
        height=params.get("height", 1024),
        num_inference_steps=params.get("num_inference_steps", 30),
        guidance_scale=params.get("guidance_scale", 7.5),
        seed=params.get("seed"),
    )
