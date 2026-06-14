"""
CHERENKOV cherenkov/execution/emitters/html_report.py
Issue #435 — HTML Test Report Emitter.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader


class HTMLReportEmitter:
    """Emits a self-contained HTML report from validation results."""

    def __init__(self) -> None:
        template_dir = Path(__file__).parent
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)), autoescape=True
        )

    def emit(self, results_dict: dict, output_path: Path) -> Path:
        template = self.env.get_template("report_template.html")

        reports = results_dict.get("reports", [])
        passed_count = sum(1 for r in reports if r.get("passed", False))
        failed_count = len(reports) - passed_count

        html_content = template.render(
            target_url=results_dict.get("target_url", "N/A"),
            total_scenarios=len(reports),
            passed_count=passed_count,
            failed_count=failed_count,
            reports=reports,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return output_path
