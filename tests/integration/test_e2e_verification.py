"""
End-to-End Deployment Verification Test Suite.
Validates that the complete multi-stage system lifecycle executes cleanly.
"""

import pytest

from scripts.verify_deployment import DeploymentVerifier


@pytest.mark.asyncio
async def test_full_system_deployment_verification() -> None:
    """Run complete in-memory deployment verification covering all 7 stages."""
    async with DeploymentVerifier(use_in_memory=True) as verifier:
        success = await verifier.run_all()
        assert success is True
        assert len(verifier.verification_results) >= 10
        for result in verifier.verification_results:
            assert result["passed"] is True, f"Failed step: {result['step']}"
