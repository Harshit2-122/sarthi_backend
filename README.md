# SARTHI Backend — Deployment Guide (Render & GitHub)

Production-grade real-time backend engine for **SARTHI: Speech to Indian Sign Language (ISL)**.

Built with **FastAPI**, **WebSockets**, and **Faster-Whisper**.

---

## 🚀 Quick Step-by-Step: Deploy to Render in 5 Minutes

### Step 1: Push This `backend/` Folder to GitHub

Open a terminal inside this `backend` folder:
```bash
cd E:\sarthi\backend

# Initialize git
git init
git add .
git commit -m "Initial commit: SARTHI Production FastAPI Backend"

# Create a new repository on github.com (e.g. 'sarthi-backend')
# Then link and push:
git branch -M main
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/sarthi-backend.git
git push -u origin main
```

---

### Step 2: Deploy on Render.com

1. Go to **[dashboard.render.com](https://dashboard.render.com)** and log in.
2. Click **New +** ➔ Select **Web Service**.
3. Choose **Build and deploy from a Git repository** and connect your GitHub account.
4. Select your **`sarthi-backend`** repository.
5. Fill in the deployment settings:
   - **Name**: `sarthi-backend` (or any name you like)
   - **Region**: Choose closest to you (e.g., Singapore / Frankfurt / Oregon)
   - **Branch**: `main`
   - **Root Directory**: *(leave blank)*
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: **Free**
6. Click **Deploy Web Service**!

Render will build and deploy your backend in ~2 minutes. Once finished, Render gives you a live public URL, for example:
👉 **`https://sarthi-backend.onrender.com`**

---

### Step 3: Connect Your Vercel Frontends to Render

Your deployed Vercel frontends are already live:
- 👩‍🏫 Teacher: `https://teacher-dashboard-opal.vercel.app`
- 🧑‍🎓 Student: `https://student-dashboard-silk-alpha.vercel.app`
- 🎨 Studio: `https://signmodelstudio.vercel.app`

Once Render gives you your URL (e.g. `https://sarthi-backend.onrender.com`), connect them in **either of two ways**:

#### Method A: Via Vercel Project Settings (Permanent)
In your Vercel Dashboard for Teacher & Student projects:
- Go to **Settings ➔ Environment Variables**
- Add:
  - `VITE_API_BASE_URL` = `https://sarthi-backend.onrender.com`
  - `VITE_WS_SPEECH_URL` = `wss://sarthi-backend.onrender.com/ws/speech` (for Teacher)
  - `VITE_WS_VIEWER_URL` = `wss://sarthi-backend.onrender.com/ws/viewer` (for Student)
- Click **Redeploy** on Vercel.

#### Method B: Via the UI Settings Button ⚙️ (Instant, Zero Redeploys)
Open `https://teacher-dashboard-opal.vercel.app` or `https://student-dashboard-silk-alpha.vercel.app` in your browser:
1. Click the **Settings ⚙️** icon in the header.
2. Paste your Render URL (`https://sarthi-backend.onrender.com`).
3. Click **Save** — it connects live immediately!

---

## 📡 Live Endpoints Provided by this Backend

| Endpoint | Protocol | Purpose |
|---|---|---|
| `/health` | HTTP GET | Healthcheck and server readiness |
| `/api/gloss` | HTTP GET | Test English to ISL token conversion |
| `/ws/speech` | WebSocket | Teacher continuous microphone & speech ingestion |
| `/ws/viewer` | WebSocket | Real-time broadcast to student screens & avatars |
