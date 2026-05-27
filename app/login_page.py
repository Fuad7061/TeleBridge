LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TeleBridge - Login</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0f0f13; color: #e0e0e0; min-height: 100vh;
    display: flex; align-items: center; justify-content: center;
  }
  .login-card {
    background: #1a1a24; border-radius: 16px; padding: 48px 40px;
    width: 100%; max-width: 400px; margin: 20px;
    border: 1px solid #2a2a3a; box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  }
  .logo { text-align: center; margin-bottom: 32px; }
  .logo h1 { font-size: 28px; font-weight: 700; color: #fff; }
  .logo p { color: #888; font-size: 14px; margin-top: 4px; }
  .logo .accent { color: #6c5ce7; }
  .form-group { margin-bottom: 20px; }
  label { display: block; font-size: 13px; font-weight: 500; color: #aaa; margin-bottom: 6px; }
  input {
    width: 100%; padding: 12px 16px; border-radius: 10px; border: 1px solid #2a2a3a;
    background: #13131e; color: #e0e0e0; font-size: 15px; outline: none;
    transition: border-color 0.2s;
  }
  input:focus { border-color: #6c5ce7; }
  input::placeholder { color: #555; }
  .btn {
    width: 100%; padding: 12px; border-radius: 10px; border: none;
    background: #6c5ce7; color: #fff; font-size: 15px; font-weight: 600;
    cursor: pointer; transition: background 0.2s;
  }
  .btn:hover { background: #5a4bd1; }
  .btn:disabled { opacity: 0.6; cursor: not-allowed; }
  .error {
    background: #2d1515; border: 1px solid #5c2020; color: #ff6b6b;
    padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-bottom: 16px;
    display: none;
  }
  .spinner { display: none; } .btn.loading .spinner { display: inline-block; }
  .btn.loading .label { display: none; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .spinner { width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.6s linear infinite; vertical-align: middle; }
</style>
</head>
<body>
<div class="login-card">
  <div class="logo">
    <h1>Tele<span class="accent">Bridge</span></h1>
    <p>Sign in to continue</p>
  </div>
  <div class="error" id="error"></div>
  <form id="loginForm" onsubmit="return handleLogin(event)">
    <div class="form-group">
      <label for="password">Password</label>
      <input type="password" id="password" placeholder="Enter password" autofocus required>
    </div>
    <button type="submit" class="btn" id="loginBtn">
      <span class="label">Sign In</span>
      <span class="spinner"></span>
    </button>
  </form>
</div>
<script>
async function handleLogin(e) {
  e.preventDefault();
  const btn = document.getElementById('loginBtn');
  const err = document.getElementById('error');
  const pass = document.getElementById('password').value;
  err.style.display = 'none'; btn.classList.add('loading');
  try {
    const r = await fetch('/api/v1/auth/login', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({password: pass})
    });
    const d = await r.json();
    if (r.ok) { window.location.href = '/'; return; }
    err.textContent = d.detail || 'Invalid password'; err.style.display = 'block';
  } catch { err.textContent = 'Connection error'; err.style.display = 'block'; }
  btn.classList.remove('loading');
}
</script>
</body>
</html>"""
