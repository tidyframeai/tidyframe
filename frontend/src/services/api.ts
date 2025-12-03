import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { toast } from 'sonner';
import { isInPaymentGracePeriod } from '@/utils/gracePeriodManager';

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: '', // Use relative path - handled by vite proxy in dev, nginx in prod
      timeout: 30000,
      withCredentials: true, // Include cookies for site password authentication
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor to add auth token
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        // Handle 401 errors (unauthorized)
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          
          // Try to refresh token
          try {
            const refreshToken = localStorage.getItem('refreshToken');
            if (refreshToken) {
              const response = await this.api.post('/api/auth/refresh', {
                refresh_token: refreshToken,
              });
              
              const { access_token, refresh_token } = response.data;
              localStorage.setItem('token', access_token);
              if (refresh_token) {
                localStorage.setItem('refreshToken', refresh_token);
              }
              
              // Retry original request
              originalRequest.headers.Authorization = `Bearer ${access_token}`;
              return this.api(originalRequest);
            }
          } catch (refreshError) {
            // Refresh failed, redirect to login
            localStorage.removeItem('token');
            localStorage.removeItem('refreshToken');
            window.location.href = '/auth/login';
            return Promise.reject(refreshError);
          }
        }

        // Handle other error codes
        if (error.response) {
          const { status, data } = error.response;
          
          switch (status) {
            case 400:
              toast.error(data.message || 'Invalid request');
              break;
            case 402: {
              // Payment Required - check grace period before redirecting
              const inGracePeriod = isInPaymentGracePeriod();

              if (inGracePeriod) {
                // User just paid, waiting for webhook processing - don't redirect
                toast.info('Your subscription is being activated. Please wait a moment...');
              } else {
                // No grace period, genuinely needs to pay
                toast.error(data.message || 'Subscription required to access this feature');
                if (data.checkout_url) {
                  // If checkout URL is absolute, use it directly
                  if (data.checkout_url.startsWith('http')) {
                    window.location.href = data.checkout_url;
                  } else {
                    // Otherwise, treat as relative path
                    window.location.href = data.checkout_url;
                  }
                } else {
                  // Default to pricing page
                  window.location.href = '/pricing';
                }
              }
              break;
            }
            case 403:
              toast.error('Access forbidden');
              break;
            case 404:
              toast.error('Resource not found');
              break;
            case 429:
              toast.error('Too many requests. Please try again later.');
              break;
            case 500:
              toast.error('Server error. Please try again later.');
              break;
            default:
              toast.error('An error occurred. Please try again.');
          }
        } else if (error.request) {
          toast.error('Network error. Please check your connection.');
        } else {
          toast.error('An unexpected error occurred.');
        }

        return Promise.reject(error);
      }
    );
  }

  // Generic HTTP methods
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.api.get(url, config);
    return response.data;
  }

  async post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.api.post(url, data, config);
    return response.data;
  }

  async put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.api.put(url, data, config);
    return response.data;
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.api.delete(url, config);
    return response.data;
  }

  async patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response: AxiosResponse<T> = await this.api.patch(url, data, config);
    return response.data;
  }

  // File upload method
  async uploadFile<T>(
    url: string,
    file: File,
    onUploadProgress?: (progressEvent: { loaded: number; total?: number }) => void
  ): Promise<T> {
    const formData = new FormData();
    formData.append('file', file);

    const response: AxiosResponse<T> = await this.api.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress,
    });

    return response.data;
  }

  // Get raw axios instance for direct use if needed
  getAxiosInstance(): AxiosInstance {
    return this.api;
  }
}

export const apiService = new ApiService();