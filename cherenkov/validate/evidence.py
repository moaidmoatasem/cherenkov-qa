"""
cherenkov/validate/evidence.py
EvidenceCollector – writes per-gate captured output to a base directory.
"""

from __future__ import annotations

from pathlib import Path


class EvidenceCollector:
    """Persist per-gate captured output and produce a summary report."""

    def __init__(self, base_dir: str = ".cherenkov/evidence") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._records: list[dict] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, name: str, passed: bool, output: str, detail: str = "") -> str:
        """Save evidence for *name* and return the absolute file path.

        File content format::

            STATUS: PASS|FAIL
            DETAIL: <detail>
            ---
            <raw captured output>
        """
        target = self.base_dir / f"{name}.txt"
        status = "PASS" if passed else "FAIL"
        content = f"STATUS: {status}\nDETAIL: {detail}\n---\n{output}"
        target.write_text(content, encoding="utf-8")
        path = str(target.resolve())
        self._records.append(
            {"name": name, "path": path, "size": target.stat().st_size}
        )
        return path

    def collect_all(self) -> list[dict]:
        """Return list of {name, path, size} for all recorded evidence files."""
        # Re-scan from disk so the method is safe even after __init__ re-use.
        results: list[dict] = []
        if self.base_dir.exists():
            for file in sorted(self.base_dir.glob("*.txt")):
                results.append(
                    {
                        "name": file.stem,
                        "path": str(file.resolve()),
                        "size": file.stat().st_size,
                    }
                )
        return results

    def summary_report(self) -> str:
        """Return a human-readable summary of all collected evidence."""
        items = self.collect_all()
        if not items:
            return "No evidence collected."
        lines = [f"Evidence summary ({len(items)} item(s)) in {self.base_dir}:", ""]
        for item in items:
            lines.append(
                f"  {item['name']:<40}  {item['size']:>6} bytes  {item['path']}"
            )
        return "\n".join(lines)
