import { apiService } from './api';
import { APIKey, APIKeyCreated, CreateAPIKeyRequest } from '@/types/apiKeys';

class ApiKeyService {
  private readonly baseUrl = '/api/apikeys';

  async listAPIKeys(): Promise<APIKey[]> {
    return await apiService.get<APIKey[]>(`${this.baseUrl}/`);
  }

  async createAPIKey(request: CreateAPIKeyRequest): Promise<APIKeyCreated> {
    return await apiService.post<APIKeyCreated>(`${this.baseUrl}/`, request);
  }

  async deleteAPIKey(keyId: string): Promise<void> {
    await apiService.delete(`${this.baseUrl}/${keyId}`);
  }

  async toggleAPIKeyStatus(keyId: string): Promise<APIKey> {
    return await apiService.patch<APIKey>(`${this.baseUrl}/${keyId}/toggle`);
  }
}

export const apiKeyService = new ApiKeyService();