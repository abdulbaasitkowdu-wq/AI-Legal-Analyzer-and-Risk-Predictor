# ⚖️ AI Legal Analyzer and Risk Predictor

An intelligent legal document analysis platform that leverages Google's Gemini AI to parse, understand, and extract critical insights from contracts and legal texts. The system evaluates documents for potential risks, detects common legal clauses, generates summaries, and extracts important deadlines to automatically sync with your calendar.

## ✨ Key Features

*   **🔍 AI-Powered Document Analysis:** Upload contracts in `.pdf` or `.docx` format to automatically detect key clauses (e.g., Indemnification, Termination, Liability Limits).
*   **⚠️ Risk Scoring System:** Each document receives a computed risk score (High, Medium, Low) based on the presence of risky phrases and one-sided clauses.
*   **📅 Calendar Synchronization:** Automatically extracts dates and deadlines from documents and generates calendar events.
*   **📊 Comprehensive Admin Dashboard:** View real-time statistics, weekly upload trends, platform-wide clause detection analytics, and manage active users.
*   **🤖 AI Chat Assistant:** Interact with an integrated AI assistant to ask specific questions about your uploaded legal documents.
*   **🔐 Secure Authentication:** Full user registration and login system featuring secure `bcrypt` password hashing and role-based access control (User vs. Admin).

## 🛠️ Technology Stack

*   **Frontend:** React.js, Tailwind CSS, Lucide React (Icons), React Router
*   **Backend:** Python, FastAPI, Uvicorn
*   **Database:** MySQL
*   **AI Engine:** Google Gemini AI API (for Document Summarization, Event Extraction, and Risk Detection)
*   **Authentication:** JWT / bcrypt

## 📁 Project Structure

```text
AI_Legal_Analyzer_and_Risk_Predictor/
├── backend/                  # FastAPI Application Code
│   ├── main.py               # Core API setup and endpoints
│   ├── user_routes.py        # User profile and authentication routing
│   ├── risk_service.py       # AI Risk assessment logic
│   ├── calendar_service.py   # Event extraction logic
│   ├── chat_routes.py        # AI Chat assistant endpoints
│   ├── database.py           # MySQL Connection logic
│   └── migrations/           # Database setup and schema updates
├── frontend/                 # React Application Code
│   ├── src/
│   │   ├── components/       # Reusable UI components (Dashboard, UserProfile, etc.)
│   │   ├── context/          # React Context (UserContext for Auth)
│   │   └── App.jsx           # Main React Router setup
│   └── package.json
├── QUICKSTART.md             # Setup guide and installation instructions
└── README.md                 # Project Overview
```

## 🚀 Getting Started

To run the project locally, you will need to set up your MySQL database, configure your environment variables (including your `GEMINI_API_KEY`), and install the necessary dependencies for both the frontend and backend.

Please refer to the [QUICKSTART.md](QUICKSTART.md) file for a detailed, step-by-step installation guide.

## 🔒 Security Notes

*   Ensure that your `.env` file containing your database credentials and API keys is never committed to version control.
*   The system uses `bcrypt` to hash all passwords securely before storing them in the database.

## 🤝 Contributing

When contributing to this project, please ensure you test both the backend API endpoints and the frontend React components before creating a pull request. Database schema changes should be added to the `backend/migrations` folder.
