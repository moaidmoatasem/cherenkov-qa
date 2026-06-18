import subprocess
import shutil
import re
from pydantic import BaseModel, Field
from typing import Optional

class RunQwenCodeAgentArgs(BaseModel):
    prompt: str = Field(..., description="The instruction or task to delegate to Qwen Code")
    context: Optional[str] = Field(None, description="Additional context to provide to the agent")
    files: Optional[list[str]] = Field(None, description="List of files to process")

def run_qwen_code_agent(args: RunQwenCodeAgentArgs) -> dict:
    """
    Delegates a coding or planning task to Qwen Code's headless mode.
    This maintains the separation of concerns: CHERENKOV tests/verifies, Qwen Code plans/codes.
    """
    if not shutil.which("qwen"):
        return {"status": "error", "error": "qwen not found in PATH"}
        
    cmd = ["qwen", "-p"]
    
    # Check if args is a dict or BaseModel depending on caller
    prompt = getattr(args, "prompt", args.get("prompt", "")) if isinstance(args, dict) else args.prompt
    context = getattr(args, "context", args.get("context", "")) if isinstance(args, dict) else args.context
    files = getattr(args, "files", args.get("files", [])) if isinstance(args, dict) else args.files
    
    full_prompt = prompt
    if context:
        full_prompt += f"\n\nContext:\n{context}"
    
    if files:
        files_str = " ".join([f"@{f}" for f in files])
        full_prompt = f"{files_str} {full_prompt}"
        
    cmd.append(full_prompt)
    
    try:
        # Run headless Qwen Code via CLI
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=120
        )
        
        stdout_clean = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout)
        stderr_clean = re.sub(r'\x1b\[[0-9;]*m', '', result.stderr)
        
        return {
            "status": "success" if result.returncode == 0 else "error",
            "exit_code": result.returncode,
            "stdout": stdout_clean,
            "stderr": stderr_clean,
        }
    except subprocess.TimeoutExpired as e:
        return {
            "status": "error",
            "error": "qwen code execution timed out after 120 seconds",
            "stdout": getattr(e, "stdout", "") or "",
            "stderr": getattr(e, "stderr", "") or ""
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
