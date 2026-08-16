import os
import re

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(REPO_DIR, "docs")
GITHUB_BLOB_PREFIX = "https://github.com/moaidmoatasem/cherenkov-qa/blob/main/"

LINK_PATTERN = re.compile(r'(!?\[.*?\])\(([^)]+)\)')

def resolve_target(current_file_path, target):
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return target
    
    if "#" in target:
        path_part, anchor = target.split("#", 1)
        anchor_suffix = f"#{anchor}"
    else:
        path_part = target
        anchor_suffix = ""
        
    if not path_part:
        return target
        
    if path_part.startswith("<") or "{" in path_part:
        return target

    clean_path = path_part.strip()
    current_dir = os.path.dirname(current_file_path)
    abs_target = os.path.normpath(os.path.join(current_dir, clean_path))
    
    # Handle PRODUCT_STRATEGY_ROADMAP.md -> ROADMAP.md
    if "PRODUCT_STRATEGY_ROADMAP.md" in clean_path:
        roadmap_path = os.path.join(DOCS_DIR, "ROADMAP.md")
        correct_rel = os.path.relpath(roadmap_path, current_dir).replace("\\", "/")
        return f"{correct_rel}{anchor_suffix}"

    # Handle process/ links with too many ../
    if "process/" in clean_path:
        proc_sub = clean_path[clean_path.index("process/"):]
        proc_target = os.path.join(DOCS_DIR, proc_sub)
        if os.path.exists(proc_target):
            correct_rel = os.path.relpath(proc_target, current_dir).replace("\\", "/")
            return f"{correct_rel}{anchor_suffix}"

    try:
        rel_to_docs = os.path.relpath(abs_target, DOCS_DIR)
        is_inside_docs = not rel_to_docs.startswith("..") and not os.path.isabs(rel_to_docs)
    except ValueError:
        is_inside_docs = False

    if is_inside_docs:
        if os.path.exists(abs_target):
            correct_rel = os.path.relpath(abs_target, current_dir).replace("\\", "/")
            return f"{correct_rel}{anchor_suffix}"
    
    try:
        rel_to_repo = os.path.relpath(abs_target, REPO_DIR)
        is_inside_repo = not rel_to_repo.startswith("..") and not os.path.isabs(rel_to_repo)
    except ValueError:
        is_inside_repo = False
        
    if is_inside_repo and os.path.exists(abs_target):
        clean_rel = rel_to_repo.replace("\\", "/")
        return f"{GITHUB_BLOB_PREFIX}{clean_rel}{anchor_suffix}"

    basename = os.path.basename(clean_path)
    repo_root_candidate = os.path.join(REPO_DIR, basename)
    if os.path.exists(repo_root_candidate):
        return f"{GITHUB_BLOB_PREFIX}{basename}{anchor_suffix}"
        
    docs_candidate = os.path.join(DOCS_DIR, basename)
    if os.path.exists(docs_candidate):
        correct_rel = os.path.relpath(docs_candidate, current_dir).replace("\\", "/")
        return f"{correct_rel}{anchor_suffix}"
        
    if "vision/" in clean_path:
        vision_file = clean_path[clean_path.index("vision/"):]
        vision_target = os.path.join(DOCS_DIR, vision_file)
        if os.path.exists(vision_target):
            correct_rel = os.path.relpath(vision_target, current_dir).replace("\\", "/")
            return f"{correct_rel}{anchor_suffix}"
            
    if "cherenkov/" in clean_path:
        code_file = clean_path[clean_path.index("cherenkov/"):]
        code_target = os.path.join(REPO_DIR, code_file)
        if os.path.exists(code_target):
            return f"{GITHUB_BLOB_PREFIX}{code_file}{anchor_suffix}"
            
    if "skills/" in clean_path:
        skill_file = clean_path[clean_path.index("skills/"):]
        skill_target = os.path.join(REPO_DIR, skill_file)
        if os.path.exists(skill_target):
            return f"{GITHUB_BLOB_PREFIX}{skill_file}{anchor_suffix}"

    if "scripts/" in clean_path:
        script_file = clean_path[clean_path.index("scripts/"):]
        script_target = os.path.join(REPO_DIR, script_file)
        if os.path.exists(script_target):
            return f"{GITHUB_BLOB_PREFIX}{script_file}{anchor_suffix}"

    if "agent_memory/" in clean_path:
        mem_file = clean_path[clean_path.index("agent_memory/"):]
        mem_target = os.path.join(REPO_DIR, mem_file)
        if os.path.exists(mem_target):
            return f"{GITHUB_BLOB_PREFIX}{mem_file}{anchor_suffix}"

    return target

def process_file(file_path):
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    modified = False
    
    def repl(match):
        nonlocal modified
        prefix = match.group(1)
        target = match.group(2)
        new_target = resolve_target(file_path, target)
        if new_target != target:
            modified = True
            return f"{prefix}({new_target})"
        return match.group(0)

    new_content = LINK_PATTERN.sub(repl, content)

    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    return False

def main():
    total_files = 0
    modified_files = 0
    for root, _, files in os.walk(DOCS_DIR):
        for f in files:
            if f.endswith(".md"):
                total_files += 1
                full_path = os.path.join(root, f)
                if process_file(full_path):
                    modified_files += 1
                    rel = os.path.relpath(full_path, DOCS_DIR)
                    print(f"Fixed links in: {rel}")
    print(f"Scanned {total_files} files, modified {modified_files} files.")

if __name__ == "__main__":
    main()
