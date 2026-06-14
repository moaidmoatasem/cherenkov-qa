import json
from unittest.mock import patch
from click.testing import CliRunner

from cherenkov.substrate.doctor import doctor


def test_doctor_device_flag():
    runner = CliRunner()
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
        result = runner.invoke(doctor, ["--device"])
        assert result.exit_code == 0
        assert "desktop" in result.output


def test_doctor_vlm_flag():
    runner = CliRunner()
    with patch("cherenkov.substrate.doctor._detect_ollama_vlm") as mock:
        mock.return_value = {
            "available": False,
            "model": "",
            "error": "Connection refused",
        }
        result = runner.invoke(doctor, ["--vlm"])
        assert result.exit_code == 0
        assert "Ollama" in result.output


def test_doctor_localai_flag():
    runner = CliRunner()
    with patch("cherenkov.substrate.doctor._detect_localai_vlm") as mock:
        mock.return_value = {"available": True, "model": "llava", "error": ""}
        result = runner.invoke(doctor, ["--localai"])
        assert result.exit_code == 0
        assert "LocalAI" in result.output


def test_doctor_json_output():
    runner = CliRunner()
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
                result = runner.invoke(doctor, ["--json-output"])
                assert result.exit_code == 0
                data = json.loads(result.output)
                assert "device" in data
                assert "vlm" in data
                assert "localai" in data


def test_doctor_all_flags():
    runner = CliRunner()
    result = runner.invoke(doctor, ["--device", "--vlm", "--localai"])
    assert result.exit_code == 0


def test_doctor_no_flags_shows_all():
    runner = CliRunner()
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
            mock_ollama.return_value = {
                "available": True,
                "model": "qwen2.5-vl:7b",
                "error": "",
            }
            with patch("cherenkov.substrate.doctor._detect_localai_vlm") as mock_lai:
                mock_lai.return_value = {
                    "available": False,
                    "model": "",
                    "error": "not ready",
                }
                result = runner.invoke(doctor)
                assert result.exit_code == 0
                assert "Recommendations" in result.output
                assert "localai" in result.output


def test_doctor_recommendation_cloud():
    runner = CliRunner()
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
                result = runner.invoke(doctor)
                assert "openai" in result.output
