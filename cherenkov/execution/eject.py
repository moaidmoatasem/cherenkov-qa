"""
CHERENKOV execution/eject.py — engine for ejecting standalone Playwright test suites.
Authority: v3.1 + delta.
"""
from __future__ import annotations

import os
import shutil
import json
from cherenkov.core.errors import get_logger

class EjectorEngine:
    """Manages the lifecycle of standalone Playwright test suite ejection, stripping all CHERENKOV metadata."""

    def __init__(self, run_id: str | None = None):
        self.run_id = run_id or "eject"
        self.log = get_logger("EJECT", self.run_id)
        self.stub_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../stub"))
        self.tests_src_dir = os.path.join(self.stub_dir, "generated_tests")

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

            # 2. Copy generated test files (.spec.ts)
            if not os.path.exists(self.tests_src_dir):
                self.log.warning("no generated tests source directory found")
                return False

            spec_files = [f for f in os.listdir(self.tests_src_dir) if f.endswith(".spec.ts") or f == "_scores.json"]
            if not spec_files:
                self.log.warning("no spec files found to eject")
                return False

            for f in spec_files:
                src_file = os.path.join(self.tests_src_dir, f)
                dest_file = os.path.join(tests_dest_dir, f)
                shutil.copy2(src_file, dest_file)
                self.log.info("copied test file", filename=f)

            # 3. Copy generated types file
            types_src = os.path.join(self.stub_dir, "generated-types.ts")
            types_dest = os.path.join(output_path, "generated-types.ts")
            if os.path.exists(types_src):
                shutil.copy2(types_src, types_dest)
                self.log.info("copied generated types")
            else:
                self.log.warning("generated-types.ts not found in stub folder")

            # 4. Emit a clean, standard client.ts without any CHERENKOV trace or monkeypatching hooks
            clean_client_content = """// Standalone openapi-fetch client configuration
// Stripped of all trace and interception metadata.

import createClient from "openapi-fetch";
import type { paths } from "./generated-types";

export const client = createClient<paths>({
  baseUrl: process.env.API_URL ?? "http://localhost:8000",
});
"""
            client_dest = os.path.join(output_path, "client.ts")
            with open(client_dest, "w", encoding="utf-8") as f:
                f.write(clean_client_content)
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
            config_dest = os.path.join(output_path, "playwright.config.ts")
            with open(config_dest, "w", encoding="utf-8") as f:
                f.write(clean_playwright_config)
            self.log.info("emitted standard playwright.config.ts")

            # 6. Emit a standard package.json with standard devDependencies
            clean_package_json = {
              "name": "ejected-playwright-tests",
              "version": "1.0.0",
              "private": True,
              "scripts": {
                "test": "playwright test"
              },
              "devDependencies": {
                "@playwright/test": "^1.60.0",
                "typescript": "^5.0.0",
                "@types/node": "^20.0.0"
              },
              "dependencies": {
                "openapi-fetch": "^0.17.0"
              }
            }
            package_json_dest = os.path.join(output_path, "package.json")
            with open(package_json_dest, "w", encoding="utf-8") as f:
                json.dump(clean_package_json, f, indent=2)
            self.log.info("emitted standalone package.json")

            # 7. Emit standard tsconfig.json
            clean_tsconfig = {
              "compilerOptions": {
                "target": "ES2022",
                "module": "CommonJS",
                "moduleResolution": "node",
                "esModuleInterop": True,
                "strict": True,
                "skipLibCheck": True
              }
            }
            tsconfig_dest = os.path.join(output_path, "tsconfig.json")
            with open(tsconfig_dest, "w", encoding="utf-8") as f:
                json.dump(clean_tsconfig, f, indent=2)
            self.log.info("emitted standard tsconfig.json")

            self.log.info("standalone test suite ejection completed successfully")
            return True

        except Exception as e:
            self.log.error("failed during standalone test suite ejection", error=str(e))
            return False
