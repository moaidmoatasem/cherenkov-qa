"""
Smoke test for the mobile testing pipeline.

Verifies (without requiring real devices, Maestro, or Appium):
  1. HARParser parses HTTP archive entries correctly
  2. HILParser parses human-interface log flows correctly
  3. MobileSourceAdapter dispatches to correct parsers by file extension
  4. MobilePlanStage produces at least one scenario
  5. MobileGenerateStage produces non-empty Maestro YAML per scenario
  6. MobileReviewStage passes review for generated YAML
  7. Full pipeline: plan -> generate -> review runs without errors
  8. MaestroRunner.health_check() fails gracefully (binary not installed)
  9. AppiumRunner.health_check() fails gracefully (server not running)
 10. MaestroEjector.eject() writes YAML files and README to disk
 11. AppiumEjector.eject() writes Python test files, conftest, and README
 12. MobileRAGIndex indexes and queries apps correctly
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cherenkov.sources.mobile.parsers import HARParser, HILParser
from cherenkov.sources.mobile.adapter import MobileSourceAdapter
from cherenkov.stages.mobile_plan import MobilePlanStage
from cherenkov.stages.mobile_generate import MobileGenerateStage
from cherenkov.stages.mobile_review import MobileReviewStage
from cherenkov.execution.maestro_runner import MaestroRunner
from cherenkov.execution.appium_runner import AppiumRunner
from cherenkov.execution.mobile_eject_maestro import MaestroEjector
from cherenkov.execution.mobile_eject_appium import AppiumEjector
from cherenkov.rag.mobile_index import MobileRAGIndex

errors: list[str] = []


def check(condition: bool, msg: str) -> None:
    if not condition:
        errors.append(f"FAIL: {msg}")
        print(f"  [FAIL] {msg}")
    else:
        print(f"  [OK]   {msg}")


# ── 1. HARParser ─────────────────────────────────────────────────────────────
print("1. HARParser")
with tempfile.NamedTemporaryFile(suffix=".har", delete=False, mode="w") as f:
    json.dump({
        "log": {
            "entries": [
                {"request": {"url": "https://api.example.com/login", "method": "POST"},
                 "response": {"status": 200}},
                {"request": {"url": "https://api.example.com/users", "method": "GET"},
                 "response": {"status": 404}},
            ]
        }
    }, f)
    har_path = f.name

try:
    entries = HARParser().parse(har_path)
    check(len(entries) == 2, f"parsed 2 HAR entries (got {len(entries)})")
    check(entries[0]["method"] == "POST", f"first entry is POST (got {entries[0]['method']})")
    check(entries[1]["status"] == 404, f"second entry status 404 (got {entries[1]['status']})")
    check(entries[0]["url"] == "https://api.example.com/login", "URL preserved")
finally:
    os.unlink(har_path)

# ── 2. HILParser ─────────────────────────────────────────────────────────────
print("\n2. HILParser")
hil_data = [
    {"flow_id": "f001", "name": "Login", "screens": ["home", "login"], "actions": [{"tap": "login_btn"}]},
    {"flow_id": "f002", "name": "Signup", "screens": ["home", "signup"], "actions": []},
]
with tempfile.NamedTemporaryFile(suffix=".hil", delete=False, mode="w") as f:
    json.dump(hil_data, f)
    hil_path = f.name

try:
    flows = HILParser().parse(hil_path)
    check(len(flows) == 2, f"parsed 2 flows (got {len(flows)})")
    check(flows[0].flow_id == "f001", f"first flow_id 'f001' (got {flows[0].flow_id})")
    check(flows[0].name == "Login", f"first flow name 'Login' (got {flows[0].name})")
    check(flows[1].screens == ["home", "signup"], "second flow screens preserved")
finally:
    os.unlink(hil_path)

# ── 3. MobileSourceAdapter dispatch ──────────────────────────────────────────
print("\n3. MobileSourceAdapter")
with tempfile.NamedTemporaryFile(suffix=".har", delete=False, mode="w") as f:
    json.dump({"log": {"entries": []}}, f)
    adapter_har = f.name
with tempfile.NamedTemporaryFile(suffix=".hil", delete=False, mode="w") as f:
    json.dump([], f)
    adapter_hil = f.name

try:
    adapter = MobileSourceAdapter()
    har_result = adapter.ingest(adapter_har)
    check(isinstance(har_result, list), f".har dispatched to HARParser -> list (got {type(har_result).__name__})")

    hil_result = adapter.ingest(adapter_hil)
    check(isinstance(hil_result, list), f".hil dispatched to HILParser -> list (got {type(hil_result).__name__})")

    try:
        adapter.ingest("file.xyz")
        check(False, "unsupported extension raises ValueError")
    except ValueError:
        check(True, "unsupported extension raises ValueError")
finally:
    os.unlink(adapter_har)
    os.unlink(adapter_hil)

# ── 4. MobilePlanStage ───────────────────────────────────────────────────────
print("\n4. MobilePlanStage")
plan_stage = MobilePlanStage(run_id="smoke")
plan_output = plan_stage.run()
check(plan_output.status == "ok", f"plan status == 'ok' (got {plan_output.status!r})")
check(len(plan_output.scenarios) >= 1, f"at least 1 scenario (got {len(plan_output.scenarios)})")
for s in plan_output.scenarios:
    check(bool(s.id), f"scenario {s.id!r} has non-empty id")
    check(bool(s.steps), f"scenario {s.id!r} has steps")

# ── 5. MobileGenerateStage ───────────────────────────────────────────────────
print("\n5. MobileGenerateStage")
gen_stage = MobileGenerateStage(run_id="smoke")
gen_outputs = []
for scenario in plan_output.scenarios:
    go = gen_stage.run(scenario)
    check(go.scenario_id == scenario.id, f"gen output id matches scenario id '{scenario.id}'")
    check(bool(go.yaml_content.strip()), f"non-empty YAML for scenario {scenario.id!r}")
    check("appId:" in go.yaml_content, f"YAML contains appId: for {scenario.id!r}")
    gen_outputs.append(go)

# ── 6. MobileReviewStage ─────────────────────────────────────────────────────
print("\n6. MobileReviewStage")
review_stage = MobileReviewStage(run_id="smoke")
for go in gen_outputs:
    ro = review_stage.run(go)
    check(ro.passed, f"review passes for scenario {go.scenario_id!r} (errors: {ro.errors})")
    check(ro.status == "ok", f"review status ok for {go.scenario_id!r}")

# ── 7. Full pipeline: plan -> generate -> review ──────────────────────────────
print("\n7. Full pipeline")
p2 = MobilePlanStage()
g2 = MobileGenerateStage()
r2 = MobileReviewStage()
p_out = p2.run()
all_passed = True
for sc in p_out.scenarios:
    gen = g2.run(sc)
    rev = r2.run(gen)
    if not rev.passed:
        all_passed = False
        errors.append(f"FAIL: pipeline failed for scenario {sc.id}: {rev.errors}")
check(all_passed, f"all {len(p_out.scenarios)} scenarios pass the full pipeline")

# ── 8. MaestroRunner health_check graceful failure ───────────────────────────
print("\n8. MaestroRunner.health_check (no binary)")
runner = MaestroRunner(maestro_binary="maestro-not-installed-xyz")
result = runner.health_check()
check(result is False, f"health_check returns False when binary missing (got {result!r})")

# ── 9. AppiumRunner health_check graceful failure ────────────────────────────
print("\n9. AppiumRunner.health_check (no server)")
appium = AppiumRunner(appium_server="http://127.0.0.1:19999")
result = appium.health_check()
check(result is False, f"health_check returns False when server unreachable (got {result!r})")

# ── 10. MaestroEjector ───────────────────────────────────────────────────────
print("\n10. MaestroEjector.eject")
maestro_yaml = """
- name: login_flow
  appId: com.example.app
  steps:
    - tapOn:
        text: "Login"
    - assertVisible:
        text: "Dashboard"
"""
with tempfile.TemporaryDirectory() as out_dir:
    ejector = MaestroEjector(run_id="smoke")
    result_path = ejector.eject(maestro_yaml, out_dir)
    files = list(result_path.iterdir())
    file_names = [f.name for f in files]
    check(any(f.endswith(".yaml") for f in file_names), f"at least one YAML file ejected (got {file_names})")
    check("README.md" in file_names, "README.md written")

# ── 11. AppiumEjector ────────────────────────────────────────────────────────
print("\n11. AppiumEjector.eject")
appium_yaml = """
- name: login_test
  steps:
    - tapOn: Login
    - assertVisible: Dashboard
"""
with tempfile.TemporaryDirectory() as out_dir:
    aejector = AppiumEjector(run_id="smoke")
    result_path = aejector.eject(appium_yaml, out_dir)
    files = list(result_path.iterdir())
    file_names = [f.name for f in files]
    check(any(f.startswith("test_") and f.endswith(".py") for f in file_names), f"test_*.py file ejected")
    check("conftest.py" in file_names, "conftest.py written")
    check("requirements.txt" in file_names, "requirements.txt written")
    check("README.md" in file_names, "README.md written")
    req_content = (result_path / "requirements.txt").read_text()
    check("Appium-Python-Client" in req_content, "requirements.txt includes Appium-Python-Client")

# ── 12. MobileRAGIndex ───────────────────────────────────────────────────────
print("\n12. MobileRAGIndex")
with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
    db_path = f.name

try:
    idx = MobileRAGIndex(db_path)
    idx.index_app("com.myapp", "My App", "android", "e-commerce shopping login checkout", ["home", "cart"], [{"flow": "checkout"}])
    idx.index_app("com.other", "Other App", "ios", "media streaming video playback")

    results = idx.query("login")
    check(len(results) >= 1, f"query 'login' returns at least 1 result (got {len(results)})")
    check(results[0]["app_id"] == "com.myapp", f"correct app returned for 'login' query")
    check(isinstance(results[0]["screens"], list), "screens deserialized as list")
    check(isinstance(results[0]["flows"], list), "flows deserialized as list")

    empty = idx.query("zzz_nonexistent_query_xyz")
    check(empty == [], f"no results for nonsense query (got {empty})")

    idx.index_app("com.myapp", "My App v2", "android", "updated e-commerce login")
    updated = idx.query("login")
    check(any(r["name"] == "My App v2" for r in updated), "re-indexing same app_id replaces existing")
finally:
    os.unlink(db_path)

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
if errors:
    print(f"FAILED ({len(errors)} check(s))")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    print("ALL PASSED")
    sys.exit(0)
