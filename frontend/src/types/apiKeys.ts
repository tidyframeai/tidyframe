export interface APIKey {
  id: string;
  name: string;
  key_hint: string;
  is_active: boolean;
  usage_count: number;
  last_used_at?: string;
  created_at: string;
  expires_at?: string;
}

export interface APIKeyCreated {
  id: string;
  name: string;
  api_key: string; // Full API key - only shown once
  key_hint: string;
  expires_at?: string;
  created_at: string;
}

export interface CreateAPIKeyRequest {
  name: string;
  expires_days?: number;
}