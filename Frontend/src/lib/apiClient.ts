import axios from 'axios';

// Resolve API base URL from environment for deployment
// Vite env var: VITE_API_BASE_URL=https://django-msvx.onrender.com
const API_BASE_URL =
  (typeof import.meta !== 'undefined' && (import.meta as any).env?.VITE_API_BASE_URL) ||
  (typeof window !== 'undefined' && (window as any).__API_BASE_URL) ||
  'http://localhost:8000';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor to add auth token to requests
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    // Only add token if it's a request to our own API
    const isInternalRequest = !config.url?.startsWith('http') || config.url.startsWith(API_BASE_URL);
    if (token && isInternalRequest) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
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
