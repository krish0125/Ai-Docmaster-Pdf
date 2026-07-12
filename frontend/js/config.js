// Shared API Configuration for AI DocMaster
// TODO: replace with real Render backend URL after first deploy
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:5001'
  : 'https://YOUR_RENDER_BACKEND_URL.onrender.com';
