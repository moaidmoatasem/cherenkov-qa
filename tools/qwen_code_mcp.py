import subprocess
import json
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
    
    cmd = ["qwen", "-p"]
    
    full_prompt = args.prompt
    if args.context:
        full_prompt += f"\n\nContext:\n{args.context}"
    
    if args.files:
        files_str = " ".join([f"@{f}" for f in args.files])
        full_prompt = f"{files_str} {full_prompt}"
        
    cmd.append(full_prompt)
    
    try:
        # Run headless Qwen Code via CLI
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        return {
            "status": "success" if result.returncode == 0 else "error",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
