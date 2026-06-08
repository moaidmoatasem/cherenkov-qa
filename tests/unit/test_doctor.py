import unittest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from cherenkov.substrate.doctor import doctor


class TestDoctorCommand(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_doctor_device_flag(self):
        with patch("cherenkov.substrate.doctor._detect_device") as mock:
            mock.return_value = {
                "device_class": "desktop",
                "vlm_tier": "local",
                "has_gpu": False,
                "has_docker": False,
                "os_name": "Windows",
                "cpu_count": 8,
                "memory_gb": 16.0,
            }
            result = self.runner.invoke(doctor, ["--device"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("desktop", result.output)

    def test_doctor_vlm_flag(self):
        with patch("cherenkov.substrate.doctor._detect_ollama_vlm") as mock:
            mock.return_value = {"available": False, "model": "", "error": "Connection refused"}
            result = self.runner.invoke(doctor, ["--vlm"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Ollama", result.output)

    def test_doctor_localai_flag(self):
        with patch("cherenkov.substrate.doctor._detect_localai_vlm") as mock:
            mock.return_value = {"available": True, "model": "llava", "error": ""}
            result = self.runner.invoke(doctor, ["--localai"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("LocalAI", result.output)

    def test_doctor_json_output(self):
        with patch("cherenkov.substrate.doctor._detect_device") as mock_dev:
            mock_dev.return_value = {
                "device_class": "desktop",
                "vlm_tier": "none",
                "has_gpu": False,
                "has_docker": False,
                "os_name": "Windows",
                "cpu_count": 8,
                "memory_gb": 16.0,
            }
            with patch("cherenkov.substrate.doctor._detect_ollama_vlm") as mock_ollama:
                mock_ollama.return_value = {"available": False, "model": "", "error": ""}
                with patch("cherenkov.substrate.doctor._detect_localai_vlm") as mock_lai:
                    mock_lai.return_value = {"available": False, "model": "", "error": ""}
                    result = self.runner.invoke(doctor, ["--json-output"])
                    self.assertEqual(result.exit_code, 0)
                    import json
                    data = json.loads(result.output)
                    self.assertIn("device", data)
                    self.assertIn("vlm", data)
                    self.assertIn("localai", data)

    def test_doctor_all_flags(self):
        result = self.runner.invoke(doctor, ["--device", "--vlm", "--localai"])
        self.assertEqual(result.exit_code, 0)

    def test_doctor_no_flags_shows_all(self):
        with patch("cherenkov.substrate.doctor._detect_device") as mock_dev:
            mock_dev.return_value = {
                "device_class": "desktop",
                "vlm_tier": "local",
                "has_gpu": True,
                "has_docker": True,
                "os_name": "Linux",
                "cpu_count": 16,
                "memory_gb": 32.0,
            }
            with patch("cherenkov.substrate.doctor._detect_ollama_vlm") as mock_ollama:
                mock_ollama.return_value = {"available": True, "model": "qwen2.5-vl:7b", "error": ""}
                with patch("cherenkov.substrate.doctor._detect_localai_vlm") as mock_lai:
                    mock_lai.return_value = {"available": False, "model": "", "error": "not ready"}
                    result = self.runner.invoke(doctor)
                    self.assertEqual(result.exit_code, 0)
                    self.assertIn("Recommendations", result.output)
                    self.assertIn("localai", result.output)

    def test_doctor_recommendation_cloud(self):
        with patch("cherenkov.substrate.doctor._detect_device") as mock_dev:
            mock_dev.return_value = {
                "device_class": "desktop",
                "vlm_tier": "cloud",
                "has_gpu": False,
                "has_docker": False,
                "os_name": "Windows",
                "cpu_count": 8,
                "memory_gb": 16.0,
            }
            with patch("cherenkov.substrate.doctor._detect_ollama_vlm"):
                with patch("cherenkov.substrate.doctor._detect_localai_vlm"):
                    result = self.runner.invoke(doctor)
                    self.assertIn("openai", result.output)
