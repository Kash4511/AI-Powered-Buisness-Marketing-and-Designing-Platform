import axios from 'axios';

// Resolve API base URL from environment for deployment
const getApiBaseUrl = () => {
  // 1. Check for Vite environment variables (try both standard and '1' suffix from screenshot)
  const env = (import.meta as any).env || {};
  const baseUrl = env.VITE_API_BASE_URL || env.VITE_API_BASE_URL1;
  
  if (baseUrl) {
    return baseUrl;
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
console.log(`[apiClient] Initializing with base URL: ${API_BASE_URL}`);

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
    // Log request for debugging 400/500 errors
    if (process.env.NODE_ENV !== 'production') {
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, config.data);
    }

    const token = localStorage.getItem('access_token');
<<<<<<< HEAD
    // Only add token if it's a request to our own API
    const isInternalRequest = !config.url?.startsWith('http') || config.url.startsWith(API_BASE_URL);
    if (token && isInternalRequest) {
=======
    
    // Skip token for auth endpoints to avoid expired token blocking login (401)
    const isAuthEndpoint = config.url?.includes('/api/auth/login/') || 
                          config.url?.includes('/api/auth/register/');
    
    // Only send Authorization header if:
    // 1. We have a token
    // 2. The request is NOT to an auth endpoint
    // 3. The request is to our own API (starts with /api or matches baseURL)
    const isRelative = config.url?.startsWith('/') || !config.url?.startsWith('http');
    const isSameOrigin = config.url?.startsWith(apiClient.defaults.baseURL || '');
    
    if (token && !isAuthEndpoint && (isRelative || isSameOrigin)) {
>>>>>>> Kaashifs-Branch
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
    const originalRequest = error.config;
    
    // Skip token refresh logic for auth endpoints
    const isAuthRequest = originalRequest.url?.includes('/api/auth/login/') || 
                         originalRequest.url?.includes('/api/auth/register/') ||
                         originalRequest.url?.includes('/api/auth/token/refresh/');
    
    // If it's a 401 that we can refresh, don't log an error yet to avoid console clutter
    const canRefresh = error.response?.status === 401 && !originalRequest._retry && !isAuthRequest;
    
    if (!canRefresh) {
      console.error(`[API Response Error] ${error.response?.status} ${error.config?.url}`, error.response?.data || error.message);
      if (error.response?.status === 401 && !isAuthRequest) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.dispatchEvent(new CustomEvent('auth:expired'));
      }
    }
    
    // If error is 401 and we haven't tried to refresh token yet, and it's NOT an auth request
    if (canRefresh) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        
        if (!refreshToken) {
          // No refresh token, clear tokens and let app routing handle navigation
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.dispatchEvent(new CustomEvent('auth:expired'));
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
      } catch (refreshError: any) {
        // Refresh token failed, clear tokens and let app routing handle navigation
        console.error('Token refresh failed:', refreshError.response?.status, refreshError.response?.data);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.dispatchEvent(new CustomEvent('auth:expired'));
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

export { apiClient };
