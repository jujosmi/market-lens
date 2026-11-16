# Local development reference

Run commands from the export root. The root README is the source of truth for installation, security setup, and limitations.

## Frontend only

```powershell
Push-Location frontend
npm ci
npm run dev
Pop-Location
```

## Backend only

```powershell
Push-Location backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock-py314.txt
$env:TRADE_UI_ALLOWED_ORIGINS = 'http://127.0.0.1:5173,http://localhost:5173'
..venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Pop-Location
```

## Combined loopback demo

After installing dependencies, `.\scripts\start-local.ps1` starts the API and web client. The default expects `backend/.venv/Scripts/python.exe`. `-PythonExecutable <path>` may be used for a local alternate Python 3.14 environment; it is intended for development/testing and is not stored in project configuration. `.\scripts\stop-local.ps1` stops only matching processes created by the launcher.

If the frontend port changes, pass `-WebPort` to the launcher. The script updates the explicit CORS origins and frontend API base for that invocation. Check the API OpenAPI page at `http://127.0.0.1:8000/docs` and the health route before switching the UI into FastAPI demo mode.

Do not expose services on a LAN address. Keep SEC contact values in the backend process environment and use only a Supabase publishable key in frontend configuration. Do not commit local `.env.local` files or logs.
