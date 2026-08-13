"""
CHERENKOV execution/eject.py — engine for ejecting standalone Playwright test suites.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from cherenkov.core.errors import get_logger


def _safe_dest(base_dir: str, filename: str) -> str:
    """Join *filename* onto *base_dir* and refuse any path that escapes it."""
    base = os.path.realpath(base_dir)
    dest = os.path.normpath(os.path.join(base, filename))
    if not dest.startswith(base + os.sep):
        raise ValueError(f"unsafe output path outside {base}: {dest}")
    return dest


class EjectorEngine:
    """Manages the lifecycle of standalone Playwright test suite ejection, stripping all CHERENKOV metadata."""

    def __init__(
        self,
        run_id: str | None = None,
        tests_src_dir: str | None = None,
        allow_packaged_fixtures: bool = False,
    ):
        self.run_id = run_id or "eject"
        self.log = get_logger("EJECT", self.run_id)
        self.package_root = Path(__file__).parent.parent.parent
        self.stub_dir = str(self.package_root / "stub")
        # `tests_src_dir` lets callers point at wherever `cherenkov generate
        # --output-dir <dir>` actually wrote its output (documented in
        # docs/GETTING_STARTED.md as a supported combo).
        #
        # The default must mirror `generate --output-dir`, whose default is the
        # *relative* path "stub/generated_tests" — i.e. resolved against the
        # user's cwd. Resolving it against the installed package instead meant
        # the natural `generate` -> `eject` flow read two different directories:
        # the user's tests were written under cwd, while eject shipped this
        # package's own fixtures — including the deliberately sabotaged
        # demo_weakened / demo_deleted / demo_hallucinated specs — into the
        # user's repo under a "100% standard, runs standalone" banner.
        self.tests_src_dir = tests_src_dir or str(Path.cwd() / "stub" / "generated_tests")
        # Tracked reference specs, used to keep the eject path exercisable
        # end-to-end in CI. This is a *test* affordance, so it is opt-in: a real
        # user must never silently receive this package's fixtures in place of
        # their own generated tests.
        self.fixtures_dir = str(self.package_root / "tests" / "eject_fixtures")
        self.allow_packaged_fixtures = allow_packaged_fixtures

    @staticmethod
    def _within(directory: str, base: Path) -> bool:
        """True when `directory` sits under `base`."""
        try:
            Path(directory).resolve().relative_to(Path(base).resolve())
        except ValueError:
            return False
        return True

    def _is_inside_package(self, directory: str) -> bool:
        """True when `directory` is the package's own, not something the user made.

        "Inside the package" alone is the wrong signal: in a source checkout the
        package root *is* the repo root, so a developer's own
        ./stub/generated_tests lives inside it too — and refusing that would stop
        anyone working in the repo from ejecting their own tests. What actually
        distinguishes CHERENKOV's fixtures from the user's output is whether the
        directory sits under the directory the user is working in.
        """
        return self._within(directory, self.package_root) and not self._within(
            directory, Path.cwd()
        )

    @staticmethod
    def _spec_files_in(directory: str) -> list[str]:
        """Returns the ejectable spec/score filenames in a directory (empty if none/missing)."""
        if not os.path.isdir(directory):
            return []
        return [
            f
            for f in os.listdir(directory)
            if os.path.getsize(os.path.join(directory, f)) > 0
            and (f.endswith(".spec.ts") or f == "_scores.json")
        ]

    def _resolve_tests_src(self) -> tuple[str | None, list[str]]:
        """Picks the generated-tests dir to eject from.

        Refuses to hand back a directory inside the installed package unless the
        caller explicitly opted in: those are CHERENKOV's own fixtures, and some
        of them are deliberately sabotaged. Shipping them into a user's repo
        under a success banner is the failure this product exists to catch.
        """
        primary = self._spec_files_in(self.tests_src_dir)
        if primary:
            if self._is_inside_package(self.tests_src_dir) and not self.allow_packaged_fixtures:
                self.log.error(
                    "refusing to eject from inside the cherenkov package — these are "
                    "CHERENKOV's own test fixtures, not your generated tests",
                    tests_src_dir=self.tests_src_dir,
                )
                return None, []
            return self.tests_src_dir, primary

        if self.allow_packaged_fixtures:
            fallback = self._spec_files_in(self.fixtures_dir)
            if fallback:
                self.log.warning(
                    "no generated specs found; falling back to tracked eject fixtures",
                    fixtures_dir=self.fixtures_dir,
                )
                return self.fixtures_dir, fallback

        self.log.error(
            "no generated tests found to eject; run `cherenkov generate` first, or point "
            "eject at the directory it wrote with --tests-dir",
            tests_src_dir=self.tests_src_dir,
        )
        return None, []

    def eject_suite(self, output_dir: str) -> bool:
        """Ejects the test suite to a standalone folder with standard configs and zero CHERENKOV dependencies."""
        self.log.info("starting test suite ejection", output_dir=output_dir)

        output_path = os.path.abspath(output_dir)
        tests_dest_dir = os.path.join(output_path, "tests")

        try:
            # 1. Setup fresh target directory structure
            if os.path.exists(output_path):
                self.log.info("cleaning existing output directory", path=output_path)
                shutil.rmtree(output_path)

            os.makedirs(tests_dest_dir, exist_ok=True)

            # 2. Copy generated test files (.spec.ts), falling back to tracked fixtures
            tests_src_dir, spec_files = self._resolve_tests_src()
            if not tests_src_dir:
                self.log.warning(
                    "no spec files found to eject (generated dir and fixtures both empty)"
                )
                return False
            self.log.info("reading generated tests from", tests_src_dir=tests_src_dir)

            for f in spec_files:
                src_file = os.path.join(tests_src_dir, f)
                dest_file = os.path.join(tests_dest_dir, f)
                shutil.copy2(src_file, dest_file)
                self.log.info("copied test file", filename=f)

            # 3. Copy generated types file (fall back to tracked fixture if stub copy is absent)
            # Prefer a types file the user generated next to their own tests, then
            # one under their cwd stub/, before falling back to this package's copy
            # (which describes CHERENKOV's demo API, not theirs).
            types_candidates = [
                os.path.join(os.path.dirname(tests_src_dir), "generated-types.ts"),
                os.path.join(tests_src_dir, "generated-types.ts"),
                os.path.join(str(Path.cwd() / "stub"), "generated-types.ts"),
                os.path.join(self.stub_dir, "generated-types.ts"),
                os.path.join(self.fixtures_dir, "generated-types.ts"),
            ]
            types_src = next((c for c in types_candidates if os.path.exists(c)), types_candidates[-1])
            types_dest = _safe_dest(output_path, "generated-types.ts")
            if os.path.exists(types_src):
                shutil.copy2(types_src, types_dest)
                self.log.info("copied generated types", source=types_src)
            else:
                self.log.warning(
                    "generated-types.ts not found in stub folder or fixtures"
                )

            # 4. Emit a clean, standard client.ts without any CHERENKOV trace or monkeypatching hooks
            clean_client_content = """// Standalone openapi-fetch client configuration
// Stripped of all trace and interception metadata.

import createClient from "openapi-fetch";
import type { paths } from "./generated-types";

export const client = createClient<paths>({
  baseUrl: process.env.API_URL ?? "http://localhost:8000",
});
"""
            client_dest = _safe_dest(output_path, "client.ts")
            with open(client_dest, "w", encoding="utf-8") as fh:
                fh.write(clean_client_content)
            self.log.info("emitted clean standalone client.ts")

            # 5. Emit a standard playwright.config.ts configured to run tests/ folder
            clean_playwright_config = """import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 30000,
  expect: {
    timeout: 5000,
  },
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: process.env.API_URL ?? "http://localhost:8000",
  },
});
"""
            config_dest = _safe_dest(output_path, "playwright.config.ts")
            with open(config_dest, "w", encoding="utf-8") as fh:
                fh.write(clean_playwright_config)
            self.log.info("emitted standard playwright.config.ts")

            # 6. Emit a standard package.json with standard devDependencies
            clean_package_json = {
                "name": "ejected-playwright-tests",
                "version": "1.0.0",
                "private": True,
                "scripts": {"test": "playwright test"},
                "devDependencies": {
                    "@playwright/test": "^1.60.0",
                    "typescript": "^5.0.0",
                    "@types/node": "^20.0.0",
                },
                "dependencies": {"openapi-fetch": "^0.17.0"},
            }
            package_json_dest = _safe_dest(output_path, "package.json")
            with open(package_json_dest, "w", encoding="utf-8") as fh:
                json.dump(clean_package_json, fh, indent=2)
            self.log.info("emitted standalone package.json")

            # 7. Emit standard tsconfig.json
            clean_tsconfig = {
                "compilerOptions": {
                    "target": "ES2022",
                    "module": "CommonJS",
                    "moduleResolution": "node",
                    "esModuleInterop": True,
                    "strict": True,
                    "skipLibCheck": True,
                }
            }
            tsconfig_dest = _safe_dest(output_path, "tsconfig.json")
            with open(tsconfig_dest, "w", encoding="utf-8") as fh:
                json.dump(clean_tsconfig, fh, indent=2)
            self.log.info("emitted standard tsconfig.json")

            self.log.info("standalone test suite ejection completed successfully")
            return True

        except Exception as e:
            self.log.error("failed during standalone test suite ejection", error=str(e))
            return False
