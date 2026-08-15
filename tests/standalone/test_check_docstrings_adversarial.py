"""
test_check_docstrings_adversarial.py
─────────────────────────────────────
Adversarial stress and negative testing harness for scripts/check_docstrings.py.
Empirically verifies that scripts/check_docstrings.py strictly enforces 100% docstring
coverage and rejects missing module, class, function, parameter, and return docstrings,
as well as Go package and exported symbol comments, syntax errors, and edge cases.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.check_docstrings import run_docstring_check, CoverageStats, Violation


def test_scenario_01_fully_compliant(tmp_path: Path) -> None:
    """Stress Test 1: Verify 100% compliant Python & Go code returns exit 0 and zero violations."""
    py_dir = tmp_path / "py_src"
    go_dir = tmp_path / "go_src"
    py_dir.mkdir()
    go_dir.mkdir()

    (py_dir / "service.py").write_text(
        '"""Service module for task execution."""\n\n'
        'class ServiceRunner:\n'
        '    """Runner managing task execution cycle."""\n'
        '    def __init__(self, name: str, timeout: int = 30) -> None:\n'
        '        """Initialize runner.\n\n'
        '        Args:\n'
        '            name: Service identifier.\n'
        '            timeout: Execution timeout in seconds.\n'
        '        """\n'
        '        self.name = name\n'
        '        self.timeout = timeout\n\n'
        '    def execute(self, payload: dict) -> bool:\n'
        '        """Execute service with payload.\n\n'
        '        Args:\n'
        '            payload: Input dictionary.\n\n'
        '        Returns:\n'
        '            bool: True on success.\n'
        '        """\n'
        '        return bool(payload)\n',
        encoding="utf-8",
    )

    (go_dir / "engine.go").write_text(
        '// Package engine provides core orchestration logic.\n'
        'package engine\n\n'
        '// Engine handles background jobs.\n'
        'type Engine struct{}\n\n'
        '// Start launches the engine background loop.\n'
        'func (e *Engine) Start() error {\n'
        '    return nil\n'
        '}\n\n'
        '// Version denotes the engine build version.\n'
        'const Version = "2.0.0"\n\n'
        '// DefaultTimeout holds default timeout.\n'
        'var DefaultTimeout = 30\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], ["go_src"])
    assert len(violations) == 0
    assert stats.coverage_percentage == 100.0


def test_scenario_02_missing_module_docstring(tmp_path: Path) -> None:
    """Stress Test 2: File missing module docstring must trigger MODULE violation."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    (py_dir / "mod.py").write_text(
        'def helper() -> None:\n'
        '    """Helper func."""\n'
        '    pass\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], [])
    assert any(v.category == "MODULE" and v.file_path == "py_src\\mod.py" or v.file_path == "py_src/mod.py" for v in violations)
    assert stats.coverage_percentage < 100.0


def test_scenario_03_private_module_excluded(tmp_path: Path) -> None:
    """Stress Test 3: Private module starting with underscore should be excluded from MODULE docstring requirement."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    (py_dir / "_internal_util.py").write_text(
        'def _internal_func():\n'
        '    pass\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], [])
    assert len(violations) == 0
    assert stats.modules_total == 0


def test_scenario_04_init_py_requires_module_docstring(tmp_path: Path) -> None:
    """Stress Test 4: __init__.py is a public package root and MUST require a module docstring."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    (py_dir / "__init__.py").write_text(
        '# Empty package init without docstring\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], [])
    assert any(v.category == "MODULE" for v in violations)


def test_scenario_05_missing_class_docstring(tmp_path: Path) -> None:
    """Stress Test 5: Public class lacking docstring must trigger CLASS violation."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    (py_dir / "cls_test.py").write_text(
        '"""Module docstring."""\n\n'
        'class DatabaseClient:\n'
        '    def connect(self) -> None:\n'
        '        """Connect to DB."""\n'
        '        pass\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], [])
    assert any(v.category == "CLASS" and v.symbol_name == "DatabaseClient" for v in violations)


def test_scenario_06_private_class_excluded(tmp_path: Path) -> None:
    """Stress Test 6: Private class starting with underscore is excluded from CLASS requirement."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    (py_dir / "cls_test.py").write_text(
        '"""Module docstring."""\n\n'
        'class _PrivateHelper:\n'
        '    pass\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], [])
    assert len(violations) == 0
    assert stats.classes_total == 0


def test_scenario_07_missing_function_docstring(tmp_path: Path) -> None:
    """Stress Test 7: Public function lacking docstring must trigger FUNCTION violation."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    (py_dir / "func_test.py").write_text(
        '"""Module docstring."""\n\n'
        'def compute_hash(data: str) -> str:\n'
        '    return data\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], [])
    assert any(v.category == "FUNCTION" and v.symbol_name == "compute_hash" for v in violations)


def test_scenario_08_private_function_excluded(tmp_path: Path) -> None:
    """Stress Test 8: Private function starting with underscore is excluded from FUNCTION requirement."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    (py_dir / "func_test.py").write_text(
        '"""Module docstring."""\n\n'
        'def _internal_calc(a: int) -> int:\n'
        '    return a * 2\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], [])
    assert len(violations) == 0
    assert stats.functions_total == 0


def test_scenario_09_missing_parameter_description(tmp_path: Path) -> None:
    """Stress Test 9: Public function with undocumented parameter must trigger PARAMETER violation."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    (py_dir / "param_test.py").write_text(
        '"""Module docstring."""\n\n'
        'def transform(source: str, target: str, overwrite: bool = False) -> None:\n'
        '    """Transform source to target.\n\n'
        '    Args:\n'
        '        source: Source file path.\n'
        '        target: Target destination path.\n'
        '    """\n'
        '    pass\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], [])
    assert any(v.category == "PARAMETER" and "transform.overwrite" in v.symbol_name for v in violations)


def test_scenario_10_missing_return_description(tmp_path: Path) -> None:
    """Stress Test 10: Public function returning value lacking return description must trigger RETURN violation."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    (py_dir / "ret_test.py").write_text(
        '"""Module docstring."""\n\n'
        'def fetch_status() -> int:\n'
        '    """Fetch status code from upstream server."""\n'
        '    return 200\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], [])
    assert any(v.category == "RETURN" and v.symbol_name == "fetch_status" for v in violations)


def test_scenario_11_return_none_does_not_require_return_doc(tmp_path: Path) -> None:
    """Stress Test 11: Function returning None (or annotated -> None) should not require return description."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    (py_dir / "none_test.py").write_text(
        '"""Module docstring."""\n\n'
        'def log_event(message: str) -> None:\n'
        '    """Log an incoming event message.\n\n'
        '    Args:\n'
        '        message: Log entry string.\n'
        '    """\n'
        '    pass\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], [])
    assert len(violations) == 0
    assert stats.returns_total == 0


def test_scenario_12_init_parameters_in_class_docstring_passes(tmp_path: Path) -> None:
    """Stress Test 12: Describing __init__ parameters in the class docstring is valid and must pass."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    (py_dir / "class_args.py").write_text(
        '"""Module docstring."""\n\n'
        'class ClusterManager:\n'
        '    """Manager for Kubernetes clusters.\n\n'
        '    Args:\n'
        '        kubeconfig: Path to kubeconfig file.\n'
        '        namespace: Default k8s namespace.\n'
        '    """\n'
        '    def __init__(self, kubeconfig: str, namespace: str = "default") -> None:\n'
        '        self.kubeconfig = kubeconfig\n'
        '        self.namespace = namespace\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], [])
    assert len(violations) == 0
    assert stats.params_covered == 2


def test_scenario_13_init_parameters_missing_fails(tmp_path: Path) -> None:
    """Stress Test 13: Omitting __init__ parameters from both class and __init__ must trigger PARAMETER violation."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    (py_dir / "class_args.py").write_text(
        '"""Module docstring."""\n\n'
        'class ClusterManager:\n'
        '    """Manager for Kubernetes clusters."""\n'
        '    def __init__(self, kubeconfig: str, namespace: str = "default") -> None:\n'
        '        self.kubeconfig = kubeconfig\n'
        '        self.namespace = namespace\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], [])
    assert any(v.category == "PARAMETER" and "__init__.kubeconfig" in v.symbol_name for v in violations)
    assert any(v.category == "PARAMETER" and "__init__.namespace" in v.symbol_name for v in violations)


def test_scenario_14_async_function_verification(tmp_path: Path) -> None:
    """Stress Test 14: Async functions must enforce parameter and return descriptions."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    (py_dir / "async_test.py").write_text(
        '"""Module docstring."""\n\n'
        'async def send_payload(url: str, data: dict) -> bool:\n'
        '    """Send payload over HTTP."""\n'
        '    return True\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], [])
    assert any(v.category == "PARAMETER" and "send_payload.url" in v.symbol_name for v in violations)
    assert any(v.category == "PARAMETER" and "send_payload.data" in v.symbol_name for v in violations)
    assert any(v.category == "RETURN" and v.symbol_name == "send_payload" for v in violations)


def test_scenario_15_generator_function_yield_check(tmp_path: Path) -> None:
    """Stress Test 15: Generator function yielding values must require yield/return docstring."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    (py_dir / "gen_test.py").write_text(
        '"""Module docstring."""\n\n'
        'def token_stream():\n'
        '    """Stream incoming tokens."""\n'
        '    yield "token"\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], [])
    assert any(v.category == "RETURN" and v.symbol_name == "token_stream" for v in violations)


def test_scenario_16_python_syntax_error_resilience(tmp_path: Path) -> None:
    """Stress Test 16: Malformed Python syntax must not crash the tool and must record SYNTAX_ERROR."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    (py_dir / "broken.py").write_text(
        'def broken_syntax(:\n'
        '    pass\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, ["py_src"], [])
    assert any(v.category == "SYNTAX_ERROR" for v in violations)


def test_scenario_17_go_missing_package_comment(tmp_path: Path) -> None:
    """Stress Test 17: Go package without doc comment must trigger GO_PACKAGE violation."""
    go_dir = tmp_path / "go_src"
    go_dir.mkdir()

    (go_dir / "main.go").write_text(
        'package controller\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, [], ["go_src"])
    assert any(v.category == "GO_PACKAGE" and "controller" in v.symbol_name for v in violations)


def test_scenario_18_go_short_package_comment(tmp_path: Path) -> None:
    """Stress Test 18: Go package comment with fewer than 5 characters must trigger invalid doc comment violation."""
    go_dir = tmp_path / "go_src"
    go_dir.mkdir()

    (go_dir / "main.go").write_text(
        '// a\n'
        'package controller\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, [], ["go_src"])
    assert any(v.category == "GO_PACKAGE" and "empty/invalid" in v.message for v in violations)


def test_scenario_19_go_missing_exported_symbol_comments(tmp_path: Path) -> None:
    """Stress Test 19: Exported Go struct, func, method, const, var lacking comments must trigger GO_SYMBOL violations."""
    go_dir = tmp_path / "go_src"
    go_dir.mkdir()

    (go_dir / "types.go").write_text(
        '// Package types defines API objects.\n'
        'package types\n\n'
        'type Client struct{}\n\n'
        'func NewClient() *Client {\n'
        '    return &Client{}\n'
        '}\n\n'
        'const MaxRetries = 5\n\n'
        'var DefaultEndpoint = "http://localhost"\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, [], ["go_src"])
    go_sym_violations = [v for v in violations if v.category == "GO_SYMBOL"]
    assert len(go_sym_violations) == 4
    sym_names = {v.symbol_name for v in go_sym_violations}
    assert "Client" in sym_names
    assert "NewClient" in sym_names
    assert "MaxRetries" in sym_names
    assert "DefaultEndpoint" in sym_names


def test_scenario_20_go_unexported_symbols_ignored(tmp_path: Path) -> None:
    """Stress Test 20: Unexported Go symbols (lowercase start) must be ignored."""
    go_dir = tmp_path / "go_src"
    go_dir.mkdir()

    (go_dir / "internal.go").write_text(
        '// Package internal holds helper routines.\n'
        'package internal\n\n'
        'type worker struct{}\n\n'
        'func doWork() {}\n\n'
        'const maxAttempts = 3\n\n'
        'var defaultPort = 8080\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, [], ["go_src"])
    assert len(violations) == 0
    assert stats.go_symbols_total == 1  # Only package declaration


def test_scenario_21_go_code_generated_header_skipped(tmp_path: Path) -> None:
    """Stress Test 21: Go files with 'Code generated... DO NOT EDIT' header must be skipped completely."""
    go_dir = tmp_path / "go_src"
    go_dir.mkdir()

    (go_dir / "pb.go").write_text(
        '// Code generated by protoc-gen-go. DO NOT EDIT.\n'
        'package pb\n\n'
        'type Message struct{}\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, [], ["go_src"])
    assert len(violations) == 0
    assert stats.go_symbols_total == 0


def test_scenario_22_go_zz_generated_filename_skipped(tmp_path: Path) -> None:
    """Stress Test 22: Go files named zz_generated*.go must be skipped completely."""
    go_dir = tmp_path / "go_src"
    go_dir.mkdir()

    (go_dir / "zz_generated.deepcopy.go").write_text(
        'package v1alpha1\n\n'
        'type SpecDeepCopy struct{}\n',
        encoding="utf-8",
    )

    stats, violations = run_docstring_check(tmp_path, [], ["go_src"])
    assert len(violations) == 0
    assert stats.go_files == 0


def test_scenario_23_cli_exit_code_and_json_contract(tmp_path: Path) -> None:
    """Stress Test 23: Direct CLI invocation via subprocess verifies exit codes and JSON contract."""
    py_dir = tmp_path / "py_src"
    py_dir.mkdir()

    # Create failing file
    (py_dir / "bad.py").write_text("x = 1\n", encoding="utf-8")

    cmd = [
        sys.executable,
        "scripts/check_docstrings.py",
        "--root",
        str(tmp_path),
        "--dirs",
        "py_src",
        "--go-dirs",
        "",
        "--json",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1, "CLI must exit with code 1 when violations exist"

    payload = json.loads(res.stdout)
    assert payload["status"] == "FAILED"
    assert payload["exit_code"] == 1
    assert len(payload["violations"]) >= 1
    assert payload["metrics"]["coverage_percentage"] < 100.0
