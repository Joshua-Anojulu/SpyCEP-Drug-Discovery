"""Create the lock-ordered completion barrier for all four docking stages."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from spycep_drug_discovery.docking import require_campaign_id, seal_campaign


METHODS = PROJECT_ROOT / "docs" / "methods"
STAGE_MANIFESTS = (
    METHODS / "docking_result.json",
    METHODS / "docking_result_tight.json",
    METHODS / "speb_positive_control_result.json",
    METHODS / "boron_surrogate_result.json",
)


def main() -> None:
    campaign_id = require_campaign_id()
    seal = seal_campaign(PROJECT_ROOT, campaign_id, STAGE_MANIFESTS)
    print(
        "Sealed "
        f"campaign_{campaign_id} with {seal['spawn_retry_claim_count']} retried claims "
        f"and ledger {seal['ledger_content_sha256']}."
    )


if __name__ == "__main__":
    main()
