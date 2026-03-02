import axios from 'axios';

// Resolve API base URL from environment for deployment
const getApiBaseUrl = () => {
  // 1. Check for Vite environment variable
  if (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_BASE_URL) {
    return (import.meta as any).env.VITE_API_BASE_URL;
  }
  
  // 2. Check for global window variable
  if (typeof window !== 'undefined' && (window as any).__API_BASE_URL) {
    return (window as any).__API_BASE_URL;
  }
  
  // 3. Robust detection for local/cloud development
  if (typeof window !== 'undefined') {
    const { protocol, hostname } = window.location;
    
    // Handle Replit environment
    if (hostname.includes('replit.dev')) {
      return `${protocol}//${hostname}:8000`;
    }
    
    // Default to port 8000 on current hostname (handles localhost, 127.0.0.1, etc.)
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return `http://${hostname}:8000`;
    }
    
    // For other cases, if we're not on a known production domain, try port 8000
    // But if we're on a production-like domain (vercel.app, onrender.com), 
    // we should probably use relative path or the same origin
    const isProduction = hostname.includes('vercel.app') || hostname.includes('onrender.com');
    if (!isProduction) {
      return `${protocol}//${hostname}:8000`;
    }

    // Same-origin fallback
    return `${protocol}//${hostname}`;
  }
  
  // 4. Final fallback
  return 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Runtime diagnostics for missing configuration
if (!apiClient.defaults.baseURL || typeof apiClient.defaults.baseURL !== 'string') {
  // Hard fallback to localhost if baseURL is falsy
  apiClient.defaults.baseURL = 'http://localhost:8000';
  // Non-fatal warning to help debugging on environments with missing env vars
  try {
    console.warn('API base URL was missing; defaulted to', apiClient.defaults.baseURL);
  } catch {}
}

// Add request interceptor to inject JWT token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    
    // Only send Authorization header if:
    // 1. We have a token
    // 2. The request is to our own API (starts with /api or matches baseURL)
    // This prevents sending our JWT to external services like Cloudinary on redirects.
    const isRelative = config.url?.startsWith('/') || !config.url?.startsWith('http');
    const isSameOrigin = config.url?.startsWith(apiClient.defaults.baseURL || '');
    
    if (token && (isRelative || isSameOrigin)) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// Add response interceptor to handle token refresh and debug responses
apiClient.interceptors.response.use(
  (response) => {
    if (process.env.NODE_ENV !== 'production') {
      console.log(`[API Response] ${response.status} ${response.config.url}`, response.data);
    }
    return response;
  },
  async (error) => {
    // Log response error for debugging 400 errors
    console.error(`[API Response Error] ${error.response?.status} ${error.config?.url}`, error.response?.data || error.message);
    
    const originalRequest = error.config;
    
    // If error is 401 and we haven't tried to refresh token yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        
        if (!refreshToken) {
          // No refresh token, clear tokens and let app routing handle navigation
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          return Promise.reject(error);
        }
        
        // Try to get a new token
        const response = await axios.post(
          `${apiClient.defaults.baseURL}/api/auth/token/refresh/`,
          { refresh: refreshToken }
        );
        
        const { access } = response.data;
        
        // Save new token
        localStorage.setItem('access_token', access);
        
        // Update authorization header
        originalRequest.headers.Authorization = `Bearer ${access}`;
        
        // Retry original request
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh token failed, clear tokens and let app routing handle navigation
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

export { apiClient };
