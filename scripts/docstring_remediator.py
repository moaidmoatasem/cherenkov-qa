#!/usr/bin/env python3
"""
docstring_remediator.py
───────────────────────
Iterative, AST-accurate docstring generator and updater for CHERENKOV QA.
Repeatedly detects and fixes violations one-by-one, re-parsing AST after each edit.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.check_docstrings import _check_python_file, CoverageStats, _is_none_node


def _humanize_name(name: str) -> str:
    """Convert snake_case or CamelCase to human-readable sentence case.

    Args:
        name: Identifier name to humanize.

    Returns:
        Humanized text string.
    """
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', name)
    s = s.replace('_', ' ').strip()
    return s


def _infer_param_doc(p_name: str) -> str:
    """Infer descriptive docstring for a parameter name.

    Args:
        p_name: Name of parameter.

    Returns:
        Description string for parameter.
    """
    if p_name in ("root", "root_dir", "root_path"):
        return "Root directory path."
    if p_name in ("path", "file_path", "filepath"):
        return "Path to the target file."
    if p_name in ("dir_path", "directory"):
        return "Target directory path."
    if p_name in ("config", "cfg"):
        return "Configuration options or settings."
    if p_name in ("context", "ctx"):
        return "Execution context or metadata."
    if p_name in ("session", "session_id"):
        return "Session identifier or session state."
    if p_name in ("user", "user_id"):
        return "User identifier or user object."
    if p_name in ("org", "org_id", "organization_id"):
        return "Organization identifier."
    if p_name in ("team", "team_id"):
        return "Team identifier."
    if p_name in ("project", "project_id"):
        return "Project name or identifier."
    if p_name in ("as_json", "json_format", "is_json"):
        return "Flag indicating whether output should be formatted as JSON."
    if p_name in ("quiet", "silent"):
        return "Flag indicating whether output should be suppressed."
    if p_name in ("verbose", "debug"):
        return "Flag indicating whether verbose debug output is enabled."
    if p_name in ("timeout", "timeout_sec", "timeout_seconds"):
        return "Timeout duration in seconds."
    if p_name in ("interval", "interval_sec"):
        return "Interval duration in seconds."
    if p_name in ("limit", "max_items", "max_results"):
        return "Maximum number of items to return."
    if p_name in ("offset", "skip"):
        return "Number of items to skip for pagination."
    if p_name in ("query", "search_term", "term"):
        return "Search query string."
    if p_name in ("event", "event_type"):
        return "Event object or event type identifier."
    if p_name in ("message", "msg"):
        return "Message content or description."
    if p_name in ("data", "payload"):
        return "Payload data dictionary or object."
    if p_name.startswith("is_") or p_name.startswith("has_") or p_name.startswith("do_") or p_name.startswith("should_"):
        return f"Whether to {_humanize_name(p_name)}."
    return f"{_humanize_name(p_name).capitalize()}."


def _infer_return_doc(func_name: str) -> str:
    """Infer descriptive docstring for a return value.

    Args:
        func_name: Name of function.

    Returns:
        Description string for return value.
    """
    human = _humanize_name(func_name).lower()
    if func_name.startswith("is_") or func_name.startswith("has_") or func_name.startswith("can_") or func_name.startswith("should_"):
        return f"True if {human}, False otherwise."
    if func_name.startswith("get_"):
        noun = func_name[4:]
        return f"Retrieved {_humanize_name(noun).lower()} or None if not found."
    if func_name.startswith("list_"):
        noun = func_name[5:]
        return f"List of {_humanize_name(noun).lower()}."
    if func_name.startswith("create_") or func_name.startswith("build_") or func_name.startswith("make_"):
        noun = re.sub(r'^(create|build|make)_', '', func_name)
        return f"Created {_humanize_name(noun).lower()} instance."
    if func_name.startswith("find_"):
        noun = func_name[5:]
        return f"Matching {_humanize_name(noun).lower()} or None."
    if func_name.startswith("to_"):
        target = func_name[3:]
        return f"Converted {_humanize_name(target).lower()} representation."
    if func_name in ("execute", "run", "process", "handle", "sync"):
        return "Execution results or response payload."
    return f"Result of {human}."


def _infer_func_summary(func_name: str) -> str:
    """Infer a summary line for a function.

    Args:
        func_name: Name of function.

    Returns:
        Summary sentence.
    """
    human = _humanize_name(func_name)
    if func_name == "__init__":
        return "Initialize instance."
    if func_name.startswith("get_"):
        return f"Retrieve {_humanize_name(func_name[4:])}."
    if func_name.startswith("set_"):
        return f"Set {_humanize_name(func_name[4:])}."
    if func_name.startswith("is_"):
        return f"Check if {_humanize_name(func_name[3:])}."
    if func_name.startswith("has_"):
        return f"Check if has {_humanize_name(func_name[4:])}."
    if func_name.startswith("list_"):
        return f"List all {_humanize_name(func_name[5:])}."
    if func_name.startswith("create_"):
        return f"Create a new {_humanize_name(func_name[7:])}."
    if func_name.startswith("delete_") or func_name.startswith("remove_"):
        noun = re.sub(r'^(delete|remove)_', '', func_name)
        return f"Remove the specified {_humanize_name(noun)}."
    if func_name.startswith("update_"):
        return f"Update {_humanize_name(func_name[7:])}."
    return f"{human.capitalize()}."


def _infer_class_summary(class_name: str) -> str:
    """Infer a summary line for a class.

    Args:
        class_name: Name of class.

    Returns:
        Summary sentence.
    """
    human = _humanize_name(class_name)
    if class_name.endswith("Config"):
        return f"Configuration settings for {human[:-7]}."
    if class_name.endswith("Error") or class_name.endswith("Exception"):
        return f"Exception raised for {human} failures."
    if class_name.endswith("Adapter"):
        return f"Adapter implementation for {human[:-8]}."
    if class_name.endswith("Repository") or class_name.endswith("Repo"):
        return f"Repository for managing {human} entities."
    if class_name.endswith("Service"):
        return f"Service providing {human} operations."
    if class_name.endswith("Manager"):
        return f"Manager handling {human} lifecycle."
    if class_name.endswith("Runner"):
        return f"Runner executing {human} jobs."
    if class_name.endswith("Client"):
        return f"Client for interacting with {human[:-7]}."
    if class_name.endswith("State"):
        return f"State representation for {human}."
    if class_name.endswith("Stage"):
        return f"Pipeline stage for {human}."
    return f"{human} representation."


def _infer_module_summary(file_path: Path) -> str:
    """Infer a summary for a module.

    Args:
        file_path: Path to Python file.

    Returns:
        Module summary docstring.
    """
    stem = file_path.stem
    if stem == "__init__":
        pkg_name = file_path.parent.name
        return f"Package initialization for {pkg_name}."
    human = _humanize_name(stem)
    return f"{human.capitalize()} module for CHERENKOV QA."


def _apply_single_fix(content: str, file_path: Path) -> tuple[str, bool]:
    """Find and apply exactly one missing docstring fix to content.

    Args:
        content: Current file content string.
        file_path: Path of Python file.

    Returns:
        tuple[str, bool]: Updated content and True if a fix was applied, False if done.
    """
    lines = content.splitlines(keepends=True)
    tree = ast.parse(content, filename=str(file_path))

    # 1. Module docstring
    is_public_mod = not file_path.name.startswith("_") or file_path.name == "__init__.py"
    if is_public_mod and not ast.get_docstring(tree):
        summary = _infer_module_summary(file_path)
        insert_idx = 0
        while insert_idx < len(lines) and (
            lines[insert_idx].startswith("#!")
            or lines[insert_idx].startswith("# -*-")
            or lines[insert_idx].startswith("# coding")
        ):
            insert_idx += 1
        doc_text = f'"""{summary}\n"""\n'
        if insert_idx < len(lines) and lines[insert_idx].strip() != "":
            doc_text += "\n"
        lines.insert(insert_idx, doc_text)
        return "".join(lines), True

    # 2. Collect class and function violations
    class Finder(ast.NodeVisitor):
        """Represents Finder extending ast.NodeVisitor."""
        def __init__(self):
            self.class_stack = []
            self.fix_action = None

        def visit_ClassDef(self, node: ast.ClassDef):
            """Execute visit class def.

            Args:
                node: The node parameter. (ast.ClassDef)
            """
            if self.fix_action:
                return
            c_doc = ast.get_docstring(node)
            if not node.name.startswith("_") and (not c_doc or not c_doc.strip()):
                self.fix_action = ("class_doc", node, None)
                return
            self.class_stack.append(node)
            self.generic_visit(node)
            self.class_stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef):
            """Execute visit function def.

            Args:
                node: The node parameter. (ast.FunctionDef)
            """
            if self.fix_action:
                return
            self._handle_func(node)
            if not self.fix_action:
                self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            """Execute visit async function def.

            Args:
                node: The node parameter. (ast.AsyncFunctionDef)
            """
            if self.fix_action:
                return
            self._handle_func(node)
            if not self.fix_action:
                self.generic_visit(node)

        def _handle_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef):
            f_name = node.name
            if f_name.startswith("_") and f_name != "__init__":
                return

            f_doc = ast.get_docstring(node)
            f_doc_node = None
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                f_doc_node = node.body[0]

            parent_class = self.class_stack[-1] if self.class_stack else None
            parent_class_doc = ast.get_docstring(parent_class) if parent_class else None

            # Get parameter list
            params = [a.arg for a in node.args.args if a.arg not in ("self", "cls")]
            posonly = getattr(node.args, "posonlyargs", [])
            params.extend([a.arg for a in posonly if a.arg not in ("self", "cls")])
            params.extend([a.arg for a in node.args.kwonlyargs if a.arg not in ("self", "cls")])
            if node.args.vararg and node.args.vararg.arg not in ("self", "cls"):
                params.append(node.args.vararg.arg)
            if node.args.kwarg and node.args.kwarg.arg not in ("self", "cls"):
                params.append(node.args.kwarg.arg)

            if f_name == "__init__":
                if params:
                    combined_doc = (f_doc or "") + "\n" + (parent_class_doc or "")
                    combined_doc_lower = combined_doc.lower()
                    missing_p = [p for p in params if p.lower() not in combined_doc_lower]
                    if missing_p:
                        if not f_doc:
                            self.fix_action = ("init_missing_doc", node, missing_p)
                        else:
                            self.fix_action = ("doc_update", node, (f_doc_node, missing_p, False))
                return

            # Public function / method
            if not f_doc or not f_doc.strip():
                # Check return
                has_ret = False
                if node.returns and not _is_none_node(node.returns):
                    has_ret = True
                else:
                    for child in ast.walk(node):
                        if isinstance(child, ast.Return) and child.value is not None and not _is_none_node(child.value):
                            has_ret = True
                            break
                        elif isinstance(child, (ast.Yield, ast.YieldFrom)):
                            has_ret = True
                            break
                self.fix_action = ("func_missing_doc", node, (params, has_ret))
                return

            # Existing docstring: check missing parameters or return
            doc_lower = f_doc.lower()
            missing_p = [p for p in params if p.lower() not in doc_lower]
            has_ret = False
            if node.returns and not _is_none_node(node.returns):
                has_ret = True
            else:
                for child in ast.walk(node):
                    if isinstance(child, ast.Return) and child.value is not None and not _is_none_node(child.value):
                        has_ret = True
                        break
                    elif isinstance(child, (ast.Yield, ast.YieldFrom)):
                        has_ret = True
                        break

            return_keywords = ("return", "returns", "yield", "yields", ":return", ":returns", "@return", "@returns")
            missing_ret = has_ret and not any(k in doc_lower for k in return_keywords)

            if missing_p or missing_ret:
                self.fix_action = ("doc_update", node, (f_doc_node, missing_p, missing_ret))
                return

    finder = Finder()
    finder.visit(tree)

    if not finder.fix_action:
        return content, False

    action_type, node, data = finder.fix_action
    indent = " " * (node.col_offset + 4)

    if action_type == "class_doc":
        summary = _infer_class_summary(node.name)
        doc_body = f"{indent}\"\"\"{summary}\"\"\"\n"
        first_stmt = node.body[0] if node.body else None
        if first_stmt and first_stmt.lineno == node.lineno:
            class_line = lines[node.lineno - 1]
            colon_idx = class_line.rfind(":")
            header = class_line[:colon_idx + 1].rstrip() if colon_idx != -1 else class_line.rstrip()
            trailer = class_line[colon_idx + 1:].strip() if colon_idx != -1 else ""
            if trailer:
                lines[node.lineno - 1] = f"{header}\n{doc_body}{indent}{trailer}\n"
            else:
                lines.insert(node.lineno, doc_body)
        elif first_stmt:
            lines.insert(first_stmt.lineno - 1, doc_body)
        else:
            lines.insert(node.lineno, doc_body)
        return "".join(lines), True

    elif action_type in ("func_missing_doc", "init_missing_doc"):
        if action_type == "init_missing_doc":
            summary = "Initialize instance."
            params = data
            has_ret = False
        else:
            summary = _infer_func_summary(node.name)
            params, has_ret = data

        doc_lines = [f"{indent}\"\"\"{summary}"]
        if params:
            doc_lines.append("")
            doc_lines.append(f"{indent}Args:")
            for p in params:
                doc_lines.append(f"{indent}    {p}: {_infer_param_doc(p)}")
        if has_ret:
            doc_lines.append("")
            doc_lines.append(f"{indent}Returns:")
            doc_lines.append(f"{indent}    {_infer_return_doc(node.name)}")
        doc_lines.append(f"{indent}\"\"\"\n")
        doc_body = "\n".join(doc_lines)

        first_stmt = node.body[0] if node.body else None
        if first_stmt:
            stmt_lineno = first_stmt.lineno
            if hasattr(first_stmt, "decorator_list") and first_stmt.decorator_list:
                stmt_lineno = first_stmt.decorator_list[0].lineno

            stmt_line = lines[stmt_lineno - 1]
            m = re.search(r':\s*(?P<trailer>\.\.\.|pass)\s*$', stmt_line)
            if m and not isinstance(first_stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                colon_idx = m.start()
                header = stmt_line[:colon_idx + 1].rstrip()
                trailer = m.group("trailer")
                lines[stmt_lineno - 1] = f"{header}\n{doc_body}{indent}{trailer}\n"
            else:
                lines.insert(stmt_lineno - 1, doc_body)
        else:
            lines.insert(node.lineno, doc_body)
        return "".join(lines), True

    elif action_type == "doc_update":
        f_doc_node, missing_p, missing_ret = data
        if not f_doc_node:
            return content, False

        start_l = f_doc_node.lineno - 1
        end_l = f_doc_node.end_lineno if hasattr(f_doc_node, "end_lineno") and f_doc_node.end_lineno is not None else start_l + 1
        existing_doc_str = f_doc_node.value.value if isinstance(f_doc_node.value, ast.Constant) else ""

        additions = []
        if missing_p:
            if "args:" not in existing_doc_str.lower():
                additions.append("Args:")
            for p in missing_p:
                additions.append(f"    {p}: {_infer_param_doc(p)}")

        if missing_ret:
            if "returns:" not in existing_doc_str.lower() and "return:" not in existing_doc_str.lower():
                additions.append("Returns:")
                additions.append(f"    {_infer_return_doc(node.name)}")

        clean_existing = existing_doc_str.rstrip()
        extra_lines = []
        for line in additions:
            if line:
                extra_lines.append(f"{indent}{line}")
            else:
                extra_lines.append("")
        extra_text = "\n".join(extra_lines)

        formatted_lines = [f"{indent}\"\"\"{clean_existing}\n\n{extra_text}\n{indent}\"\"\"\n"]
        lines[start_l:end_l] = formatted_lines
        return "".join(lines), True

    return content, False


def remediate_file(file_path: Path, root_path: Path) -> int:
    """Repeatedly apply single fixes to file until compliant.

    Args:
        file_path: Target Python file path.
        root_path: Repository root directory.

    Returns:
        Number of fixes applied.
    """
    stats = CoverageStats()
    violations = _check_python_file(file_path, root_path, stats)
    if not violations:
        return 0

    content = file_path.read_text(encoding="utf-8")
    fixes = 0

    for iteration in range(60):
        try:
            new_content, applied = _apply_single_fix(content, file_path)
            if not applied:
                break
            # Verify syntax
            ast.parse(new_content, filename=str(file_path))
            content = new_content
            fixes += 1
        except SyntaxError as se:
            print(f"Syntax error at iteration {iteration} on {file_path}: {se}")
            break
        except Exception as e:
            print(f"Error on {file_path}: {e}")
            break

    if fixes > 0:
        file_path.write_text(content, encoding="utf-8")

    return fixes


def main():
    """Execute main CLI entry point.
    """
    root = Path(".")
    dirs = sys.argv[1:] if len(sys.argv) > 1 else [
        "cherenkov/adapters",
        "cherenkov/stages",
        "cherenkov/substrate",
        "cherenkov/chat",
        "cherenkov/healing",
        "cherenkov/execution",
        "cherenkov/ports",
        "cherenkov/divergence",
        "cherenkov/enterprise",
        "cherenkov/cli",
    ]

    total_fixed = 0
    for d in dirs:
        p_dir = Path(d)
        if not p_dir.exists():
            continue
        for py_file in p_dir.rglob("*.py"):
            fixed = remediate_file(py_file, root)
            if fixed:
                total_fixed += fixed
                print(f"Fixed {py_file} ({fixed} items)")

    print(f"Total fixes applied: {total_fixed}")


if __name__ == "__main__":
    main()
