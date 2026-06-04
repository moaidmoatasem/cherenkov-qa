import os
import tempfile
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cherenkov.core.config import Config
from cherenkov.openclaw.feedback import HealingFeedbackStore
from cherenkov.federation.corpus import Corpus


def run_sync_smoke():
    print("Starting Federation Multi-Node Sync Smoke Test...")

    # Create temp feedback databases
    db_a_fd, db_a_path = tempfile.mkstemp(suffix=".feedback_a.db")
    os.close(db_a_fd)
    db_b_fd, db_b_path = tempfile.mkstemp(suffix=".feedback_b.db")
    os.close(db_b_fd)

    store_a = HealingFeedbackStore(db_path=db_a_path)
    store_b = HealingFeedbackStore(db_path=db_b_path)

    # 1. Seed Node A with 5 'intended' classifications for '/api/users' 'missing_email'
    for i in range(5):
        store_a.record_feedback(
            item_id=f"item-{i}",
            endpoint="/api/users",
            mutation_id="missing_email",
            classification="intended",
            actor="@alice",
            detail="intentional schema shift",
        )

    # Check that Node A has the suggestion
    t_a = store_a.compute_thresholds("/api/users", "missing_email")
    assert t_a["count"] == 5
    assert t_a["dominant_classification"] == "intended"
    assert t_a["confidence"] >= 0.70

    # Check that Node B initially has 0 classifications
    t_b_init = store_b.compute_thresholds("/api/users", "missing_email")
    assert t_b_init["count"] == 0

    # 2. Test Egress = 'any'
    Config.EGRESS = "any"
    corp = Corpus()
    data = corp.export_feedback(store_a)
    assert len(data) == 5
    assert data[0]["endpoint"] == "/api/users"
    assert data[0]["actor"] == "@alice"

    # Import into B
    corp.import_feedback(store_b, data)
    t_b_sync = store_b.compute_thresholds("/api/users", "missing_email")
    assert t_b_sync["count"] == 5
    assert t_b_sync["dominant_classification"] == "intended"
    print(
        "  - Egress 'any': Sync successfully transferred raw labels and matched suggestions."
    )

    # 3. Test Egress = 'internal' (Sovereign/Anonymized sync)
    # Clear store_b
    os.unlink(db_b_path)
    db_b_fd, db_b_path = tempfile.mkstemp(suffix=".feedback_b.db")
    os.close(db_b_fd)
    store_b = HealingFeedbackStore(db_path=db_b_path)

    Config.EGRESS = "internal"
    data_internal = corp.export_feedback(store_a)
    assert len(data_internal) == 5
    # Endpoint should be hashed, not raw
    assert data_internal[0]["endpoint"] != "/api/users"
    assert data_internal[0]["actor"] == "anonymized"

    # Import into B under internal
    corp.import_feedback(store_b, data_internal)

    # Query B: thresholds query should hash input under internal matching rules
    t_b_internal = store_b.compute_thresholds("/api/users", "missing_email")
    assert t_b_internal["count"] == 5
    assert t_b_internal["dominant_classification"] == "intended"
    print(
        "  - Egress 'internal': Sync successfully transferred anonymized labels and matched suggestions."
    )

    # 4. Test Egress = 'none' (Strictly forbidden)
    Config.EGRESS = "none"
    try:
        corp.export_feedback(store_a)
        raise AssertionError("Egress 'none' did not raise PermissionError on export")
    except PermissionError:
        print("  - Egress 'none' successfully blocked export.")

    try:
        corp.import_feedback(store_b, data)
        raise AssertionError("Egress 'none' did not raise PermissionError on import")
    except PermissionError:
        print("  - Egress 'none' successfully blocked import.")

    # Cleanup
    os.unlink(db_a_path)
    os.unlink(db_b_path)
    print("Federation Sync Smoke Test: ALL PASSED!\n")


if __name__ == "__main__":
    run_sync_smoke()
