from __future__ import annotations

import json

from cherenkov.core.config import Config
from cherenkov.core.errors import get_logger
from cherenkov.substrate.certification import ModelCertificationManager
from cherenkov.substrate.provider import provider_for_tier


def run_certify(tier: str = "small", rag_report: bool = False) -> int:
    log = get_logger("CERTIFY_CLI")
    log.info("running certification", tier=tier)

    provider = provider_for_tier(tier)
    cert_mgr = ModelCertificationManager(run_id="cli_certify")

    if rag_report:
        cert, reports = cert_mgr.certify_tier_with_rag_report(tier, provider)
        print(json.dumps({
            "tier": tier,
            "certified": cert.certified,
            "faithfulness_score": cert.faithfulness_score,
            "detail": cert.detail,
            "per_item_reports": reports,
        }, indent=2))
    else:
        cert = cert_mgr.certify_tier(tier, provider)
        print("=" * 60)
        print(f"  Certification Report - Tier: {tier}")
        print("=" * 60)
        print(f"  Certified:        {'YES' if cert.certified else 'NO'}")
        print(f"  Composite Score:  {cert.faithfulness_score:.3f}")
        print(f"  Min Required:     {Config.CERTIFICATION_MIN_FAITHFULNESS}")
        print(f"  Detail:           {cert.detail}")
        print("=" * 60)

    return 0 if cert.certified else 1
