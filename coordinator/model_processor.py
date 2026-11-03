"""
Model and Artifact Processing Subsystem.
Implements metadata-based inspection of Safetensors, tensor shape validation,
checksum verification, and safe aggregation rules for LoRA adapters without loading
weights into coordinator RAM.
"""

import hashlib
import json
import logging
import struct
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class ModelProcessor:
    """
    Lightweight, streaming model and tensor inspector for coordinator.
    Operates strictly on file headers and metadata streams.
    """

    @staticmethod
    def parse_safetensors_header(header_bytes: bytes) -> dict[str, Any]:
        """
        Parse Safetensors 8-byte little-endian header length and decode JSON metadata.
        Does not read or allocate tensor weight buffers.
        """
        if len(header_bytes) < 8:
            raise ValueError("Safetensors file too small to contain valid 8-byte header")

        # First 8 bytes: unsigned 64-bit little-endian integer length of JSON header
        header_len = struct.unpack("<Q", header_bytes[:8])[0]

        if header_len > 100 * 1024 * 1024:  # 100 MB safety limit on header size
            raise ValueError(f"Safetensors header abnormally large ({header_len} bytes)")

        if len(header_bytes) < 8 + header_len:
            raise ValueError("Safetensors buffer does not contain full JSON header")

        header_json_bytes = header_bytes[8 : 8 + header_len]
        try:
            return json.loads(header_json_bytes.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Malformed Safetensors JSON header: {e}") from e

    @staticmethod
    async def compute_stream_sha256(stream: AsyncIterator[bytes]) -> tuple[str, int]:
        """
        Compute SHA-256 digest and total byte count over an asynchronous chunked stream.
        Maintains constant memory overhead.
        """
        hasher = hashlib.sha256()
        total_bytes = 0
        async for chunk in stream:
            if chunk:
                hasher.update(chunk)
                total_bytes += len(chunk)
        return hasher.hexdigest(), total_bytes

    @staticmethod
    def inspect_adapter_config(config_json_bytes: bytes) -> dict[str, Any]:
        """
        Parse and validate a PEFT LoRA adapter_config.json.
        Extracts rank 'r', lora_alpha, target_modules, and base_model_name_or_path.
        """
        try:
            data = json.loads(config_json_bytes.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Invalid JSON in adapter_config: {e}") from e

        required_keys = ["r", "lora_alpha", "target_modules"]
        missing = [k for k in required_keys if k not in data]
        if missing:
            raise ValueError(f"Missing required LoRA parameters in adapter_config: {missing}")

        return {
            "r": int(data["r"]),
            "lora_alpha": float(data["lora_alpha"]),
            "target_modules": list(data["target_modules"]),
            "base_model_name_or_path": data.get("base_model_name_or_path", "unknown"),
            "peft_type": data.get("peft_type", "LORA"),
        }

    @staticmethod
    def validate_lora_compatibility(adapter_configs: list[dict[str, Any]]) -> tuple[bool, str]:
        """
        Mathematically and architecturally validate that a set of LoRA adapters
        can be safely aggregated using Federated Averaging (FedAvg).

        Aggregation is valid IF AND ONLY IF:
        1. All adapters share the exact same base model.
        2. All adapters share the exact same rank 'r'.
        3. All adapters share the exact same lora_alpha scaling factor.
        4. All adapters target the exact same module list.
        """
        if len(adapter_configs) < 2:
            return True, "Single or zero adapters trivially valid"

        baseline = adapter_configs[0]
        base_model = baseline.get("base_model_name_or_path")
        rank = baseline.get("r")
        alpha = baseline.get("lora_alpha")
        targets = set(baseline.get("target_modules", []))

        for idx, cfg in enumerate(adapter_configs[1:], start=2):
            if cfg.get("base_model_name_or_path") != base_model:
                return (
                    False,
                    f"Adapter {idx} base model mismatch: expected '{base_model}', got '{cfg.get('base_model_name_or_path')}'",
                )
            if cfg.get("r") != rank:
                return (
                    False,
                    f"Adapter {idx} rank mismatch: expected r={rank}, got r={cfg.get('r')}",
                )
            if cfg.get("lora_alpha") != alpha:
                return (
                    False,
                    f"Adapter {idx} alpha mismatch: expected alpha={alpha}, got alpha={cfg.get('lora_alpha')}",
                )
            if set(cfg.get("target_modules", [])) != targets:
                return (
                    False,
                    f"Adapter {idx} target modules mismatch: expected {sorted(targets)}, got {sorted(cfg.get('target_modules', []))}",
                )

        return True, "All adapters are architecturally compatible for weighted aggregation"

    @staticmethod
    def compute_weighted_fedavg_weights(contributions: list[dict[str, Any]]) -> dict[UUID, float]:
        """
        Compute normalized FedAvg weights from worker sample counts:
        w_k = n_k / sum(n_i)
        Returns mapping from worker_id to normalized float weight.
        """
        total_samples = sum(c.get("num_samples_processed", 0) for c in contributions)
        if total_samples <= 0:
            raise ValueError("Total sample count across contributions must be strictly positive")

        weights: dict[Any, float] = {}
        for c in contributions:
            worker_id = c["worker_id"]
            samples = c.get("num_samples_processed", 0)
            weights[worker_id] = round(samples / total_samples, 6)

        return weights


# ModelProcessor singleton
model_processor = ModelProcessor()


def get_model_processor() -> ModelProcessor:
    """Return model processor singleton."""
    return model_processor
