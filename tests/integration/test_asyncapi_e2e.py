import os
import tempfile

TEST_ASYNCAPI = """
asyncapi: 2.6.0
info:
  title: Order Events
  version: 1.0.0
channels:
  orders/created:
    publish:
      message:
        name: OrderCreated
        payload:
          type: object
          properties:
            orderId:
              type: string
"""

def test_asyncapi_generate_integration():
    # Note: cherenkov.py does not explicitly expose an --source asyncapi yet natively,
    # but we can check if it parses or errors out. Let's run a generic test.
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(TEST_ASYNCAPI)
        temp_path = f.name

    try:
        # Even if asyncapi is not a valid choice in argparse, we test the adapter directly
        from cherenkov.sources.asyncapi.adapter import AsyncAPISourceAdapter
        from cherenkov.stages.plan_asyncapi import AsyncAPIScenarioPlanner
        
        adapter = AsyncAPISourceAdapter(temp_path)
        planner = AsyncAPIScenarioPlanner()
        scenarios = planner.plan(adapter)
        
        assert len(scenarios) > 0
        assert scenarios[0].channel == "orders/created"
        
    finally:
        os.unlink(temp_path)
