"""
Unit tests for metadata-based Safetensors inspection and LoRA adapter compatibility validation.
"""

import json
import struct
import uuid

from coordinator.model_processor import ModelProcessor


def test_safetensors_header_parsing() -> None:
    """Verify parsing Safetensors 8-byte little-endian header without reading tensors."""
    sample_metadata = {
        "__metadata__": {"format": "pt", "framework": "transformers"},
        "model.layers.0.self_attn.q_proj.weight": {
            "dtype": "F16",
            "shape": [4096, 4096],
            "data_offsets": [0, 33554432],
        },
    }
    json_bytes = json.dumps(sample_metadata).encode("utf-8")
    header_len = len(json_bytes)
    # Pack 8-byte little-endian integer length followed by JSON bytes
    file_bytes = struct.pack("<Q", header_len) + json_bytes

    parsed = ModelProcessor.parse_safetensors_header(file_bytes)
    assert "__metadata__" in parsed
    assert "model.layers.0.self_attn.q_proj.weight" in parsed
    assert parsed["model.layers.0.self_attn.q_proj.weight"]["shape"] == [4096, 4096]


def test_lora_compatibility_validation() -> None:
    """Verify mathematical and architectural validation of LoRA adapters for FedAvg."""
    cfg1 = {
        "base_model_name_or_path": "mistralai/Mistral-7B-v0.1",
        "r": 16,
        "lora_alpha": 32.0,
        "target_modules": ["q_proj", "v_proj"],
    }

    cfg2_compatible = {
        "base_model_name_or_path": "mistralai/Mistral-7B-v0.1",
        "r": 16,
        "lora_alpha": 32.0,
        "target_modules": ["q_proj", "v_proj"],
    }

    cfg3_rank_mismatch = {
        "base_model_name_or_path": "mistralai/Mistral-7B-v0.1",
        "r": 32,  # Different rank
        "lora_alpha": 32.0,
        "target_modules": ["q_proj", "v_proj"],
    }

    cfg4_target_mismatch = {
        "base_model_name_or_path": "mistralai/Mistral-7B-v0.1",
        "r": 16,
        "lora_alpha": 32.0,
        "target_modules": ["q_proj", "k_proj"],  # Different targets
    }

    # 1. Compatible adapters
    valid, reason = ModelProcessor.validate_lora_compatibility([cfg1, cfg2_compatible])
    assert valid is True

    # 2. Rank mismatch
    valid_rank, reason_rank = ModelProcessor.validate_lora_compatibility([cfg1, cfg3_rank_mismatch])
    assert valid_rank is False
    assert "rank mismatch" in reason_rank

    # 3. Target module mismatch
    valid_tgt, reason_tgt = ModelProcessor.validate_lora_compatibility([cfg1, cfg4_target_mismatch])
    assert valid_tgt is False
    assert "target modules mismatch" in reason_tgt


def test_weighted_fedavg_weights_calculation() -> None:
    """Verify calculation of normalized sample weights for federated aggregation."""
    w1 = uuid.uuid4()
    w2 = uuid.uuid4()
    w3 = uuid.uuid4()

    contributions = [
        {"worker_id": w1, "num_samples_processed": 500},
        {"worker_id": w2, "num_samples_processed": 1000},
        {"worker_id": w3, "num_samples_processed": 500},
    ]

    weights = ModelProcessor.compute_weighted_fedavg_weights(contributions)
    assert weights[w1] == 0.25
    assert weights[w2] == 0.50
    assert weights[w3] == 0.25
    assert round(sum(weights.values()), 4) == 1.0
