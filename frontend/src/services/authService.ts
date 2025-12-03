import { apiService } from './api';
import { User, LoginResponse, LoginRequest, ConsentData } from '@/types/auth';

class AuthService {
  async login(email: string, password: string): Promise<LoginResponse> {
    const data: LoginRequest = { email, password };
    return await apiService.post<LoginResponse>('/api/auth/login', data);
  }

  async register(email: string, password: string, fullName?: string, consent?: ConsentData): Promise<LoginResponse> {
    // Split fullName into first_name and last_name for backend compatibility
    const nameParts = fullName?.trim().split(' ') || [];
    const firstName = nameParts[0] || undefined;
    const lastName = nameParts.slice(1).join(' ') || undefined;
    
    const data = { 
      email, 
      password, 
      first_name: firstName,
      last_name: lastName,
      consent: consent
    };
    return await apiService.post<LoginResponse>('/api/auth/register', data);
  }

  async logout(): Promise<void> {
    await apiService.post('/api/auth/logout');
  }

  async getCurrentUser(): Promise<User> {
    return await apiService.get<User>('/api/user/profile');
  }

  async updateProfile(data: Partial<User>): Promise<User> {
    return await apiService.put<User>('/api/user/profile', data);
  }

  async resetPassword(email: string): Promise<void> {
    await apiService.post('/api/auth/reset-password', { email });
  }

  async verifyEmail(token: string): Promise<void> {
    await apiService.post('/api/auth/verify-email', { token });
  }

  async refreshToken(refreshToken: string): Promise<{ token: string }> {
    return await apiService.post<{ token: string }>('/api/auth/refresh', {
      refreshToken,
    });
  }

  // API key management for enterprise users
  async createApiKey(name: string): Promise<{ key: string; keyHint: string }> {
    return await apiService.post<{ key: string; keyHint: string }>('/api/user/api-keys', {
      name,
    });
  }

  async deleteApiKey(keyId: string): Promise<void> {
    await apiService.delete(`/api/user/api-keys/${keyId}`);
  }

  async getApiKeys(): Promise<Array<{ id: string; name: string; keyHint: string; createdAt: string }>> {
    return await apiService.get('/api/user/api-keys');
  }
}

export const authService = new AuthService();