// Shared API Configuration for AI DocMaster
// When running locally via serve.py (port 5500), use empty string so all
// API calls go through the built-in reverse proxy — no CORS issues.
// In production (Render/Vercel etc.), set this to your deployed backend URL.
const API_BASE_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? ''   // same-origin proxy: serve.py forwards /auth /pdf /ocr /ai etc. → backend:5001
  : 'https://YOUR_RENDER_BACKEND_URL.onrender.com';
