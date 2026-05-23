import axios from 'axios';

// Resolve API base URL from environment for deployment
const getApiBaseUrl = () => {
  // 1. Check for Vite environment variables
  const env = (import.meta as any).env || {};
  let baseUrl = env.VITE_API_BASE_URL || env.VITE_API_BASE_URL1 || env.VITE_API_URL;
  
  // 2. Check for global window variable
  if (!baseUrl && typeof window !== 'undefined' && (window as any).__API_BASE_URL) {
    baseUrl = (window as any).__API_BASE_URL;
  }
  
  // 3. Robust detection for local/cloud development
  if (!baseUrl && typeof window !== 'undefined') {
    const { protocol, hostname } = window.location;
    
    if (hostname.includes('replit.dev')) {
      baseUrl = `${protocol}//${hostname}:8000`;
    } else if (hostname === 'localhost' || hostname === '127.0.0.1') {
      baseUrl = `http://${hostname}:8000`;
    } else {
      const isProduction = hostname.includes('vercel.app') || hostname.includes('onrender.com');
      if (isProduction) {
        // If we are on Vercel, the backend is on Render. 
        // If we are on Render, we use the current origin.
        baseUrl = hostname.includes('vercel.app') 
          ? 'https://django-msvx.onrender.com' 
          : `${protocol}//${hostname}`;
      } else {
        baseUrl = `${protocol}//${hostname}:8000`;
      }
    }
  }
  
  baseUrl = baseUrl || 'https://django-msvx.onrender.com';

  // Sanitize: Remove trailing slashes (Django + Axios work best with leading slashes in requests)
  return baseUrl.replace(/\/+$/, "");
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
}

// Helper to sanitize paths: ALWAYS ensures a leading slash
// This works perfectly with baseURLs that have no trailing slash
const fixPath = (path: string) => {
  if (!path) return path;
  if (path.startsWith('http')) return path;
  
  let cleaned = path;
  // Ensure leading slash
  if (!cleaned.startsWith('/')) {
    cleaned = `/${cleaned}`;
  }
  // Ensure trailing slash for Django endpoints (unless it has a file extension)
  if (!cleaned.endsWith('/') && !cleaned.includes('.')) {
    cleaned = `${cleaned}/`;
  }
  return cleaned;
};

// Add request interceptor to handle path cleaning and auth
apiClient.interceptors.request.use(
  (config) => {
    // 1. Fix path joining
    if (config.url) {
      config.url = fixPath(config.url);
    }

    // 2. If data is FormData, let the browser/axios set the Content-Type with boundary
    if (config.data instanceof FormData) {
      if (config.headers) {
        delete config.headers['Content-Type'];
      }
    }

    // 3. Log request for debugging
    const fullUrl = config.url?.startsWith('http') 
      ? config.url 
      : `${config.baseURL}${config.url}`;
      
    if (process.env.NODE_ENV !== 'production') {
      console.log(`[API Request] ${config.method?.toUpperCase()} ${fullUrl}`, {
        path: config.url,
        baseURL: config.baseURL,
        data: config.data
      });
    }

    const token = localStorage.getItem('access_token');
    
    // Improved check for auth and same origin
    const isAuthEndpoint = config.url?.includes('/auth/login/') || 
                          config.url?.includes('/auth/register/');
    
    // Check if same origin (either relative path or matches baseURL)
    const isRelative = !config.url?.startsWith('http');
    const isSameOrigin = config.url?.startsWith(apiClient.defaults.baseURL || '');
    
    if (token && !isAuthEndpoint && (isRelative || isSameOrigin)) {
      config.headers.Authorization = `Bearer ${token}`;
    } else if (token && !isAuthEndpoint) {
      // Diagnostic log for why token was skipped
      console.debug(`[apiClient] Skipping token for ${config.url}: isRelative=${isRelative}, isSameOrigin=${isSameOrigin}`);
    }
    
    return config;
  },
  (error) => {
    // Suppress console spam for aborted requests or known 404 retries handled by UI
    if (axios.isCancel(error)) return Promise.reject(error);
    return Promise.reject(error);
  }
);

// Add response interceptor to handle token refresh and debug responses
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;
    const url = originalRequest?.url;
    
    // Skip token refresh logic for auth endpoints
    const isAuthRequest = url?.includes('/api/auth/login/') || 
                         url?.includes('/api/auth/register/') ||
                         url?.includes('/api/auth/token/refresh/');
    
    // If it's a 401 that we can refresh, don't log an error yet to avoid console clutter
    const canRefresh = status === 401 && !originalRequest._retry && !isAuthRequest;
    
    if (!canRefresh) {
      const data = error.response?.data;
      
      // ── 404 Not Found Handling ──
      if (status === 404) {
        const isAIEndpoint = url?.includes('/api/ai-chat/') || url?.includes('/api/ai-conversation/');
        const fullUrl = `${apiClient.defaults.baseURL}${url}`;
        let msg = `Endpoint not found: ${url}`;
        let details = `The server returned a 404 for ${fullUrl}. Check if the backend route is registered in urls.py.`;
        
        if (isAIEndpoint) {
          msg = 'AI Service Unavailable (404)';
          details = `The AI service endpoint (${fullUrl}) was not found. This often happens if the backend deployment is not complete or the route name changed.`;
        }
        
        console.error(`[apiClient] 404 Error: ${msg}`, { url, fullUrl, details });
        const finalError = new Error(msg);
        (finalError as any).details = details;
        (finalError as any).status = 404;
        (finalError as any).fullUrl = fullUrl;
        (finalError as any).response = error.response;
        return Promise.reject(finalError);
      }

      // ── 500 Internal Server Error Handling ──
      if (status === 500) {
        let errorMessage = 'Server Error (500)';
        let errorDetails = '';
        
        // Handle ArrayBuffer responses
        if (data instanceof ArrayBuffer) {
          try {
            const text = new TextDecoder('utf-8').decode(data);
            if (text.trim().startsWith('{')) {
              const jsonData = JSON.parse(text);
              errorMessage = jsonData.error || jsonData.message || errorMessage;
              errorDetails = jsonData.details || '';
            }
          } catch (e) {}
        } else if (data && typeof data === 'object') {
          errorMessage = data.error || data.message || errorMessage;
          errorDetails = data.details || '';
        }
        
        const finalError = new Error(errorMessage);
        (finalError as any).details = errorDetails;
        (finalError as any).status = 500;
        (finalError as any).response = error.response;
        return Promise.reject(finalError);
      }

      if (status === 401 && !isAuthRequest) {
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
