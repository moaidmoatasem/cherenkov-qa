"""
CHERENKOV Week 0 — Controllable Target API
The "test range." A clean OpenAPI spec + a bug toggle so you can prove green->red.

Run NORMAL (Days 1-3):   uvicorn target_api:app --reload --port 8000
Run REGRESSION (Day 4):  REGRESSION_MODE=true uvicorn target_api:app --reload --port 8000
Get the spec:            curl http://localhost:8000/openapi.json > ../stub/target_spec.json
"""
import os
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field


app = FastAPI(
    title="CHERENKOV Week 0 Target",
    version="1.0.0",
    description="Controllable API for proving AI test generation catches regressions.",
)

REGRESSION_MODE = os.getenv("REGRESSION_MODE", "false").lower() == "true"


# FastAPI returns 422 for validation errors by default. We normalize to 400,
# and in regression mode we inject BUG 1: swallow the error and return 200.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    if REGRESSION_MODE:
        # BUG 1 — wrong status: returns 200 instead of 400.
        # A test asserting toBe(400) will FAIL. A shallow test (status < 500) passes.
        return JSONResponse(status_code=200, content={"message": "ok (mock)"})
    errors = [
        {"field": str(e["loc"][-1]) if e["loc"] else "unknown", "error": e["type"]}
        for e in exc.errors()
    ]
    return JSONResponse(
        status_code=400, content={"detail": "Validation failed", "errors": errors}
    )


class UserCreate(BaseModel):
    email: str = Field(..., max_length=50, description="User email address")
    password: str = Field(..., min_length=8, description="User password")


class UserResponse(BaseModel):
    id: int
    email: str


@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate):
    if REGRESSION_MODE:
        # BUG 2 — body shape: returns 'user_id' instead of 'id'.
        # A test asserting toHaveProperty('id') will FAIL.
        return {"user_id": 42, "email": user.email}
    return UserResponse(id=42, email=user.email)


@app.get("/health", status_code=200)
async def health_check():
    return {"status": "ok", "regression_mode": REGRESSION_MODE}


@app.get("/", response_class=HTMLResponse)
async def home_page():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CHERENKOV Control Panel</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #09090b;
      --card-bg: rgba(24, 24, 27, 0.6);
      --border: rgba(63, 63, 70, 0.4);
      --accent: #2563eb;
      --accent-glow: rgba(37, 99, 235, 0.4);
      --text: #fafafa;
      --text-muted: #a1a1aa;
      --success: #10b981;
      --error: #ef4444;
    }
    
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    
    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: 'Inter', sans-serif;
      min-height: 100vh;
      display: flex;
      justify-content: center;
      align-items: center;
      overflow: hidden;
      position: relative;
    }
    
    body::before {
      content: '';
      position: absolute;
      width: 400px;
      height: 400px;
      background: radial-gradient(circle, var(--accent-glow) 0%, transparent 70%);
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      z-index: -1;
      filter: blur(80px);
    }
    
    .card {
      background: var(--card-bg);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 40px;
      width: 100%;
      max-width: 420px;
      box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
      animation: fadeIn 0.6s ease-out;
    }
    
    h1 {
      font-size: 24px;
      font-weight: 700;
      margin-bottom: 8px;
      background: linear-gradient(135deg, #fafafa 0%, #a1a1aa 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      letter-spacing: -0.5px;
    }
    
    p.subtitle {
      color: var(--text-muted);
      font-size: 14px;
      margin-bottom: 24px;
    }
    
    .form-group {
      margin-bottom: 20px;
      display: flex;
      flex-direction: column;
    }
    
    label {
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-muted);
      margin-bottom: 6px;
    }
    
    input {
      background: rgba(9, 9, 11, 0.8);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px 16px;
      color: var(--text);
      font-size: 14px;
      outline: none;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    input:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px var(--accent-glow);
    }
    
    .btn {
      width: 100%;
      background: var(--accent);
      color: #fff;
      border: none;
      border-radius: 8px;
      padding: 14px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      box-shadow: 0 4px 12px var(--accent-glow);
      position: relative;
      overflow: hidden;
    }
    
    .btn:hover {
      background: #1d4ed8;
      box-shadow: 0 6px 18px var(--accent-glow);
      transform: translateY(-1px);
    }
    
    .btn:active {
      transform: translateY(1px);
    }
    
    .message {
      margin-top: 16px;
      padding: 12px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 500;
      text-align: center;
      display: none;
      animation: slideIn 0.3s ease-out;
    }
    
    .message.success {
      background: rgba(16, 185, 129, 0.1);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: var(--success);
      display: block;
    }
    
    .message.error {
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: var(--error);
      display: block;
    }
    
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes slideIn {
      from { opacity: 0; transform: translateY(-5px); }
      to { opacity: 1; transform: translateY(0); }
    }
  </style>
</head>
<body>

  <div class="card">
    <h1>Create QA User</h1>
    <p class="subtitle">Enter details to register a user on the target mock range.</p>
    
    <form id="user-form" onsubmit="submitForm(event)">
      <div class="form-group">
        <label for="email-input">Email Address</label>
        <input type="text" id="email-input" placeholder="qa@cherenkov.local" required autocomplete="off">
      </div>
      
      <div class="form-group">
        <label for="password-input">Password</label>
        <input type="password" id="password-input" placeholder="••••••••" required autocomplete="off">
      </div>
      
      <button type="submit" id="submit-button" class="btn">Register User</button>
    </form>
    
    <div id="feedback-message" class="message"></div>
  </div>

  <script>
    async function submitForm(event) {
      event.preventDefault();
      const email = document.getElementById('email-input').value;
      const password = document.getElementById('password-input').value;
      const feedback = document.getElementById('feedback-message');
      const submitBtn = document.getElementById('submit-button');
      
      submitBtn.disabled = true;
      submitBtn.innerText = 'Registering...';
      feedback.className = 'message';
      feedback.style.display = '';
      
      try {
        const response = await fetch('/users', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (response.status === 201) {
          feedback.innerText = `Success: User created with ID ${data.id || data.user_id}`;
          feedback.className = 'message success';
        } else {
          let errorMsg = data.detail || 'Registration failed';
          if (data.errors && data.errors.length > 0) {
            errorMsg += ': ' + data.errors.map(e => `${e.field} (${e.error})`).join(', ');
          }
          feedback.innerText = errorMsg;
          feedback.className = 'message error';
        }
      } catch (err) {
        feedback.innerText = 'Network error or server offline';
        feedback.className = 'message error';
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerText = 'Register User';
      }
    }
  </script>
</body>
</html>"""

