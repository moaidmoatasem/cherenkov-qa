#!/usr/bin/env python3
"""
smoke_test_rag.py — local RAG Learning Stage integration smoke test.
Proves relational event schemas, SQLite indexing, and cosine similarity searches.
"""

import os
import sys

from cherenkov.ai.rag_index import RAGIndex


def run_rag_smoke_tests():
    print("=======================================================")
    print("      CHERENKOV TRACK C RAG LEARNING SMOKE TEST")
    print("=======================================================\n")

    # Clean existing RAG db to ensure fresh test runs
    db_path = ".cherenkov/rag_store.db"
    if os.path.exists(db_path):
        print(f"Cleaning existing RAG database at {db_path}...")
        os.remove(db_path)

    # 1. Initialize RAG Index
    print("Pass 1: Initializing RAG SQLite Index...")
    rag = RAGIndex(run_id="rag_smoke")
    assert os.path.exists(db_path), "Failed to initialize RAG SQLite file."
    print("✓ SQLite database initialized successfully.\n")

    # 2. Add Incidents
    print("Pass 2: Adding failure incidents to RAG vector database...")
    rag.add_incident(
        incident_id="inc_001",
        scenario_id="create_user_400",
        failure_class="CONTRACT_DRIFT",
        error_message="Expected property 'id' missing from response",
    )
    rag.add_incident(
        incident_id="inc_002",
        scenario_id="auth_expiry_401",
        failure_class="AUTH_EXPIRY",
        error_message="Auth token expired on request execution",
    )
    rag.add_incident(
        incident_id="inc_003",
        scenario_id="sequence_404",
        failure_class="STATE_SEQUENCE",
        error_message="Stale user resource was not found on path",
    )
    print("✓ Three historical failure incidents indexed cleanly.\n")

    # 3. Query Similar Incidents (Cosine Similarity Check)
    print("Pass 3: Querying vector RAG index for matching incidents...")
    results = rag.query_similar_incidents(
        error_message="Expected 'id' key was missing", limit=2
    )

    assert len(results) > 0, "Query returned no matching incidents."
    print(f"✓ Found {len(results)} matching incident vectors:")
    for res in results:
        print(
            f"  - Incident: {res['id']} | Similarity: {res['similarity']} | Msg: {res['error_message']}"
        )

    # Assert that the list is sorted by similarity descending
    if len(results) > 1:
        assert (
            results[0]["similarity"] >= results[1]["similarity"]
        ), "Incidents are not sorted by similarity descending."
        print("\n✓ Correct cosine similarity descending order verified.")

    print("\n=======================================================")
    print("      CHERENKOV RAG LEARNING SMOKE TESTS PASSED!")
    print("=======================================================")


if __name__ == "__main__":
    try:
        run_rag_smoke_tests()
        sys.exit(0)
    except Exception as e:
        print(f"\n🛑 RAG Smoke Test Failed: {e}")
        sys.exit(1)
