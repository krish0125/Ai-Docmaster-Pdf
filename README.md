# AI DocMaster – High-Speed Intelligent PDF and Image Processing Platform

AI DocMaster is a fast, AI-powered platform for intelligent PDF and image processing, featuring OCR, text summarization, document merging/splitting/compressing, and a real-time document chat interface.

## Core Features

- **PDF Operations**: Merge multiple PDFs, split PDFs into specific pages, and compress PDFs to reduce size.
- **OCR Text Extraction**: Extract text from images (PNG, JPG, JPEG) and scanned PDFs using Tesseract OCR and OpenCV.
- **AI Summary Generator**: Summarize documents, extract key points, or format study/exam notes using BART-large-CNN transformers (with an extractive CPU/memory-efficient fallback).
- **Chat with PDF**: Interact directly with your documents in real-time using the Google Gemini API.
- **Resume Analyzer**: Scan resumes for ATS compatibility, detect skills, get suggestions, and list missing requirements for a target role.
- **JWT Auth & File Management**: User registration, login, and visual dashboard to manage recent documents and project history.

## Project Structure

```text
AI-DocMaster/
├── frontend/             # Single-page visual app (HTML, CSS, JS)
│   ├── index.html        # Landing page
│   ├── login.html        # Login & signup portal
│   ├── dashboard.html    # Core dashboard with inline utility sections
│   ├── chat.html         # Interactive PDF chat room
│   ├── css/              # Glassmorphism dark-theme styling
│   └── js/               # Frontend API integration scripts
└── backend/              # Flask Backend Server
    ├── app.py            # Main server entrypoint & blueprint mapping
    ├── config.py         # Config variables
    ├── database/         # MongoDB initialization and CRUD helpers
    ├── middleware/       # JWT auth filters
    ├── routes/           # REST endpoints
    ├── services/         # PDF processing algorithms
    └── ai_modules/       # Tesseract OCR, Summarizer, and Gemini engines
```

## Setup Instructions

### Prerequisites
1. **Python 3.8+**
2. **MongoDB** (local server running on port `27017` or MongoDB Atlas URI)
3. **Tesseract OCR** system binary installed (on Windows: default is `C:\Program Files\Tesseract-OCR\tesseract.exe`)

### Backend Setup
1. Open a terminal in the `backend/` directory:
   ```bash
   cd backend
   ```
2. Install the Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the template env file or edit the `.env` file in the project root:
   ```env
   # MongoDB Connection
   MONGO_URI=mongodb://localhost:27017/
   MONGO_DB_NAME=ai_docmaster

   # Gemini API Key (get from https://aistudio.google.com)
   GEMINI_API_KEY=your_gemini_api_key_here

   # JWT Secret Key
   JWT_SECRET_KEY=your-super-secret-jwt-key-change-this

   # Tesseract OCR Path (Windows default)
   TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
   ```
4. Run the Flask server:
   ```bash
   python app.py
   ```
   The backend will run on `http://localhost:5000`.

### Frontend Setup
1. Host the `frontend/` folder using any static web server (such as Live Server in VS Code, Python's built-in server, or simply opening `index.html` in the browser).
   - If using python's built-in server, run:
     ```bash
     cd frontend
     python -m http.server 5500
     ```
2. Navigate to `http://localhost:5500` or open the pages in your browser.
