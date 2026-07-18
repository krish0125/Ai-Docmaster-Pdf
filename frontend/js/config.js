// Shared API Configuration for AI DocMaster
// When running locally via serve.py (port 5500), use empty string so all
// API calls go through the built-in reverse proxy — no CORS issues.
// In production (Render/Vercel etc.), set this to your deployed backend URL.
const API_BASE_URL = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? ''   // same-origin proxy: serve.py forwards /auth /pdf /ocr /ai etc. → backend:5001
  : 'https://ai-docmaster-pdf-kk.onrender.com';

if (API_BASE_URL.includes('YOUR_RENDER_BACKEND_URL')) {
  console.warn("WARNING: API_BASE_URL is still using the placeholder 'YOUR_RENDER_BACKEND_URL'. AI tools will fail. Please update config.js with your actual deployed Render URL.");
}

/**
 * Resilient fetch wrapper for all API calls.
 * Catches network-level failures (e.g. CORS, offline, backend sleeping) 
 * and surfaces a user-friendly error instead of leaking TypeError.
 */
window.safeFetch = async function (url, options) {
  try {
    const response = await fetch(url, options);
    return response;
  } catch (error) {
    if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
      // It's a network error (CORS, server down, waking up, or no internet)
      throw new Error("Could not reach the server. Please check your connection or try again shortly. If the server is waking up, it might take a few seconds.");
    }
    throw error;
  }
};