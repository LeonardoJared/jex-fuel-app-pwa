# JEX Fuel - Sistema de Control y Despacho de Combustible
Plataforma integral para el registro, supervisión y despacho de combustible en operaciones de campo y minería.

## 🏗️ Arquitectura del Sistema
* **Backend API**: FastAPI + SQLAlchemy 2.0 + PostgreSQL (Neon Cloud) + Argon2id.
* **Frontend PWA**: PWA móvil offline-ready con IndexedDB y Service Workers.
* **Dashboard Admin**: Panel corporativo en Streamlit para monitoreo y altas maestras.

## 🚀 Comandos de Ejecución Local

### 1. Backend (API)
```bash
cd backend
python -m uvicorn main:app --reload --port 8000

## 2. Frontend PWA (Móvil)
code
Bash
cd frontend_pwa
python -m http.server 5500
Acceso: http://localhost:5500

## 3. Dashboard Admin (Streamlit)
code
Bash
streamlit run dashboard_admin/app_visual.py