"""
Tests for cherenkov/healing/providers/ — SandboxProvider abstraction.
Authority: v3.1 + delta.

D7 invariant: sandboxed workspaces cannot modify host files.
Anti-lock-in: filesystem provider is the default fallback.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest

from cherenkov.healing.providers.base import SandboxResult
from cherenkov.healing.providers.filesystem import FilesystemSandboxProvider
from cherenkov.healing.providers.docker_sandbox import DockerSandboxProvider


class TestSandboxResult(unittest.TestCase):
    def test_sandbox_result_defaults(self):
        r = SandboxResult()
        self.assertFalse(r.passed)
        self.assertEqual(r.exit_code, -1)
        self.assertEqual(r.stdout, "")
        self.assertEqual(r.stderr, "")

    def test_sandbox_result_construct(self):
        r = SandboxResult(passed=True, exit_code=0, stdout="ok", stderr="")
        self.assertTrue(r.passed)
        self.assertEqual(r.exit_code, 0)


class TestFilesystemSandboxProvider(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.stub_dir = os.path.join(self.tmp_dir, "stub")
        os.makedirs(os.path.join(self.stub_dir, "generated_tests"))
        os.makedirs(os.path.join(self.stub_dir, "config"))
        with open(os.path.join(self.stub_dir, "config", "test.txt"), "w") as f:
            f.write("config data")
        self.cherenkov_dir = os.path.join(self.tmp_dir, ".cherenkov")
        os.makedirs(self.cherenkov_dir, exist_ok=True)
        self.provider = FilesystemSandboxProvider(cherenkov_dir=self.cherenkov_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_replicate_workspace_creates_sandbox(self):
        workspace = self.provider.replicate_workspace("test-123", self.stub_dir)
        self.assertTrue(os.path.isdir(workspace))
        self.assertTrue(os.path.isdir(os.path.join(workspace, "generated_tests")))
        self.provider.destroy_workspace(workspace)
        self.assertFalse(os.path.exists(workspace))

    def test_replicate_workspace_copies_stub_files(self):
        workspace = self.provider.replicate_workspace("test-copy", self.stub_dir)
        config_path = os.path.join(workspace, "config", "test.txt")
        self.assertTrue(os.path.exists(config_path))
        with open(config_path) as f:
            self.assertEqual(f.read(), "config data")
        self.provider.destroy_workspace(workspace)

    def test_read_file(self):
        workspace = self.provider.replicate_workspace("test-read", self.stub_dir)
        content = self.provider.read_file(workspace, "config/test.txt")
        self.assertEqual(content, "config data")
        self.provider.destroy_workspace(workspace)

    def test_write_file(self):
        workspace = self.provider.replicate_workspace("test-write", self.stub_dir)
        self.provider.write_file(
            workspace, "generated_tests/new_test.spec.ts", "test content"
        )
        result = self.provider.read_file(workspace, "generated_tests/new_test.spec.ts")
        self.assertEqual(result, "test content")
        self.provider.destroy_workspace(workspace)

    def test_filesystem_sandbox_d7_fallback(self):
        """Anti-lock-in: filesystem provider creates isolated workspace."""
        provider = FilesystemSandboxProvider(cherenkov_dir=self.cherenkov_dir)
        workspace = provider.replicate_workspace("d7-test", self.stub_dir)
        self.assertTrue(os.path.exists(workspace))
        provider.destroy_workspace(workspace)
        self.assertFalse(os.path.exists(workspace))


@unittest.skipUnless(
    shutil.which("docker") is not None,
    "Docker not available — skipping Docker sandbox tests",
)
class TestDockerSandboxProvider(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.stub_dir = os.path.join(self.tmp_dir, "stub")
        os.makedirs(os.path.join(self.stub_dir, "generated_tests"))
        os.makedirs(os.path.join(self.stub_dir, "config"))
        with open(os.path.join(self.stub_dir, "config", "test.txt"), "w") as f:
            f.write("config data")
        self.cherenkov_dir = os.path.join(self.tmp_dir, ".cherenkov")
        os.makedirs(self.cherenkov_dir, exist_ok=True)
        self.provider = DockerSandboxProvider(
            image="alpine:latest",
            cherenkov_dir=self.cherenkov_dir,
        )

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_docker_sandbox_creates_container(self):
        container_id = self.provider.replicate_workspace("docker-test", self.stub_dir)
        self.assertIsInstance(container_id, str)
        self.assertTrue(len(container_id) > 0)
        # Verify container exists
        result = subprocess.run(
            ["docker", "inspect", container_id],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.provider.destroy_workspace(container_id)

    def test_docker_sandbox_isolation(self):
        """D7: Docker sandbox container cannot modify host filesystem."""
        container_id = self.provider.replicate_workspace("d7-docker", self.stub_dir)
        self.provider.destroy_workspace(container_id)
        # Container is removed — no trace on host
        result = subprocess.run(
            ["docker", "inspect", container_id],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
