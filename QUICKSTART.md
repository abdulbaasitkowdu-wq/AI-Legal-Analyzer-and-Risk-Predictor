# Quick Start Guide - Run Your Project

## 🚀 Quick Setup (5-10 minutes)

### Step 1: Update Environment Variables
Edit `backend/.env` with your actual credentials:

```env
# MySQL Database Configuration
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_DATABASE=legal_analyzer_db
MYSQL_USER=root
MYSQL_PASSWORD=your_actual_password

# Get GEMINI_API_KEY from: https://aistudio.google.com/app/apikeys
GEMINI_API_KEY=your_actual_gemini_key

# Google OAuth (optional, for Calendar sync)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

### Step 2: Run Database Migrations
Open your MySQL client and execute these SQL files in order:

```bash
# Using MySQL CLI:
mysql -u root -p legal_analyzer_db < backend/migrations/000_create_users_table.sql
mysql -u root -p legal_analyzer_db < backend/migrations/001_add_analysis_json.sql
mysql -u root -p legal_analyzer_db < backend/migrations/002_create_events_table.sql
mysql -u root -p legal_analyzer_db < backend/migrations/003_chat_assistant.sql

# Or open each .sql file in MySQL Workbench and execute
```

### Step 3: Install Dependencies
From the project root directory:

```bash
npm install
cd backend && pip install -r requirements.txt
cd ../frontend && npm install
cd ..
```

### Step 4: Run Everything

#### Option A: Run Both Frontend & Backend Together
```bash
npm run dev
```
This will:
- Backend: `http://localhost:8000` (FastAPI)
- Frontend: `http://localhost:3001` (React)

#### Option B: Run Separately

**Terminal 1 - Backend:**
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm start
```

## ✅ Verify Everything Works

1. **Backend Health Check:**
   Open: `http://localhost:8000/docs`
   (You should see Swagger API documentation)

2. **Frontend:**
   Open: `http://localhost:3001`
   (You should see the React app)

3. **Database Connection:**
   The backend will log "Successfully connected to MySQL database" on startup

## 🛠️ Troubleshooting

### MySQL Connection Failed
- Check username/password in `backend/.env`
- Ensure MySQL service is running
- Verify database name exists

### GEMINI_API_KEY Error
- Get key from: https://aistudio.google.com/app/apikeys
- Make sure it's added to `backend/.env`
- Restart backend after updating

### Port Already in Use
- Backend (8000): `netstat -ano | findstr :8000` then `taskkill /PID <pid> /F`
- Frontend (3001): Edit the port in `frontend/package.json` start script

### Dependencies Not Installing
```bash
# Clear cache and retry
pip cache purge
npm cache clean --force
```

## 📂 Project Structure

```
├── backend/
│   ├── main.py            # FastAPI app
│   ├── database.py        # MySQL connection
│   ├── requirements.txt   # Python packages
│   ├── .env              # Your config (UPDATE THIS)
│   └── migrations/        # SQL files (RUN THESE)
├── frontend/
│   ├── src/
│   ├── package.json      # Node packages
│   └── public/
└── package.json          # Root config (run dev/backend/frontend)
```

## 🔗 API Endpoints

- `POST /api/chat/` - Chat with Gemini
- `POST /api/events/` - Create events
- `GET /api/events/` - List events
- `POST /api/documents/` - Upload documents
- `POST /api/auth/login` - Login
- `POST /api/auth/register` - Register

Check `http://localhost:8000/docs` for full API documentation.

---

**Need help?** Check backend logs in terminal and browser console (F12) for frontend errors.
