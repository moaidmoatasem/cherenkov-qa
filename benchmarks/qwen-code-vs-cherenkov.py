from deepeval import evaluate
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from qwen_code_mcp import run_qwen_code_agent
from cherenkov.agents.copilot import CopilotAgent

# Dummy metrics setup
relevancy_metric = AnswerRelevancyMetric(threshold=0.7)


def test_qwen_code_generation():
    prompt = "Write a pytest test for the POST /api/v1/users endpoint checking for 201 Created."

    # Run Qwen Code
    qwen_result = run_qwen_code_agent({"prompt": prompt, "files": []})
    qwen_output = qwen_result.get("stdout", "")

    test_case = LLMTestCase(
        input=prompt,
        actual_output=qwen_output,
        expected_output="def test_create_user():\n    assert response.status_code == 201",
    )

    evaluate([test_case], [relevancy_metric])


def test_cherenkov_generation():
    prompt = "Write a pytest test for the POST /api/v1/users endpoint checking for 201 Created."

    # Run CHERENKOV Copilot
    agent = CopilotAgent()
    cherenkov_output = agent.generate(prompt)

    test_case = LLMTestCase(
        input=prompt,
        actual_output=cherenkov_output,
        expected_output="def test_create_user():\n    assert response.status_code == 201",
    )

    evaluate([test_case], [relevancy_metric])


if __name__ == "__main__":
    print("Running DeepEval benchmarks: Qwen Code vs CHERENKOV Copilot...")
    # This is a stub for the full benchmark suite
