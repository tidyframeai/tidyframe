import { apiService } from './api';

export interface AdminUser {
  id: string;
  email: string;
  plan: string;
  parsesThisMonth: number;
  monthlyLimit: number;
  customMonthlyLimit?: number;
  isActive: boolean;
  emailVerified: boolean;
  createdAt: string;
  lastLoginAt?: string;
}

export interface SystemStats {
  total_users: number;
  active_users: number;
  total_jobs: number;
  jobs_today: number;
  total_parses: number;
  parses_today: number;
  storage_used_gb: number;
}

export interface UserLimitUpdate {
  customMonthlyLimit?: number;
}

export interface UserPlanUpdate {
  plan: string;
}

export interface UsageResetRequest {
  reset_count?: number;
}

// Backend API response types (snake_case from backend)
interface BackendUserResponse {
  id: string;
  email: string;
  plan: string;
  parses_this_month: number;
  monthly_limit: number;
  custom_monthly_limit?: number;
  is_active: boolean;
  email_verified: boolean;
  created_at: string;
  last_login_at?: string;
}

interface BackendUserDetailsResponse {
  user: BackendUserResponse;
  statistics: {
    total_jobs: number;
    total_parses: number;
    current_month_parses: number;
  };
}

class AdminService {
  private baseUrl = '/api/admin';

  // Get system statistics
  async getSystemStats(): Promise<SystemStats> {
    const data = await apiService.get<SystemStats>(`${this.baseUrl}/stats`);
    return data; // Backend already uses snake_case which matches our interface
  }

  // List all users with pagination and filtering
  async getUsers(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    plan_filter?: string;
  }): Promise<AdminUser[]> {
    const searchParams = new URLSearchParams();
    
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString());
    if (params?.search) searchParams.append('search', params.search);
    if (params?.plan_filter) searchParams.append('plan_filter', params.plan_filter);

    const queryString = searchParams.toString();
    const url = queryString ? `${this.baseUrl}/users?${queryString}` : `${this.baseUrl}/users`;

    const users = await apiService.get<BackendUserResponse[]>(url);

    // Transform backend snake_case to frontend camelCase
    return users.map(user => ({
      id: user.id,
      email: user.email,
      plan: user.plan,
      parsesThisMonth: user.parses_this_month,
      monthlyLimit: user.monthly_limit,
      customMonthlyLimit: user.custom_monthly_limit,
      isActive: user.is_active,
      emailVerified: user.email_verified,
      createdAt: user.created_at,
      lastLoginAt: user.last_login_at,
    }));
  }

  // Get detailed user information
  async getUserDetails(userId: string): Promise<{
    user: AdminUser;
    statistics: {
      total_jobs: number;
      total_parses: number;
      current_month_parses: number;
    };
  }> {
    const data = await apiService.get<BackendUserDetailsResponse>(`${this.baseUrl}/users/${userId}`);

    return {
      user: {
        id: data.user.id,
        email: data.user.email,
        plan: data.user.plan,
        parsesThisMonth: data.user.parses_this_month,
        monthlyLimit: data.user.monthly_limit,
        customMonthlyLimit: data.user.custom_monthly_limit,
        isActive: data.user.is_active,
        emailVerified: data.user.email_verified,
        createdAt: data.user.created_at,
        lastLoginAt: data.user.last_login_at,
      },
      statistics: data.statistics
    };
  }

  // Update user limits
  async updateUserLimits(userId: string, limits: UserLimitUpdate): Promise<{
    message: string;
    old_limit?: number;
    new_limit?: number;
    monthlyLimit: number;
  }> {
    return apiService.patch(`${this.baseUrl}/users/${userId}/limits`, limits);
  }

  // Update user plan
  async updateUserPlan(userId: string, planUpdate: UserPlanUpdate): Promise<{
    message: string;
    old_plan: string;
    new_plan: string;
    monthlyLimit: number;
  }> {
    return apiService.patch(`${this.baseUrl}/users/${userId}/plan`, planUpdate);
  }

  // Reset user usage
  async resetUserUsage(userId: string, resetData?: UsageResetRequest): Promise<{
    message: string;
    old_count: number;
    new_count: number;
  }> {
    return apiService.post(`${this.baseUrl}/users/${userId}/reset-usage`, resetData || {});
  }

  // General user update (supports all allowed fields)
  async updateUser(userId: string, updateData: { 
    is_active?: boolean;
    plan?: string; 
    email_verified?: boolean;
    customMonthlyLimit?: number;
  }): Promise<{ message: string }> {
    return apiService.put(`${this.baseUrl}/users/${userId}`, updateData);
  }

  // Get all processing jobs
  async getJobs(params?: {
    page?: number;
    page_size?: number;
    status_filter?: string;
    user_email?: string;
  }): Promise<{
    jobs: Array<{
      id: string;
      filename: string;
      status: string;
      user_email: string;
      createdAt: string;
      row_count?: number;
      progress?: number;
    }>;
  }> {
    const searchParams = new URLSearchParams();
    
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString());
    if (params?.status_filter) searchParams.append('status_filter', params.status_filter);
    if (params?.user_email) searchParams.append('user_email', params.user_email);

    const queryString = searchParams.toString();
    const url = queryString ? `${this.baseUrl}/jobs?${queryString}` : `${this.baseUrl}/jobs`;
    
    return apiService.get(url);
  }

  // Get webhook events
  async getWebhookEvents(params?: {
    page?: number;
    page_size?: number;
    processed?: boolean;
  }): Promise<{
    events: Array<{
      id: string;
      external_event_id: string;
      event_type: string;
      source: string;
      processed: boolean;
      createdAt: string;
      error_message?: string;
    }>;
  }> {
    const searchParams = new URLSearchParams();
    
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString());
    if (params?.processed !== undefined) searchParams.append('processed', params.processed.toString());

    const queryString = searchParams.toString();
    const url = queryString ? `${this.baseUrl}/webhooks?${queryString}` : `${this.baseUrl}/webhooks`;
    
    return apiService.get(url);
  }
}

export const adminService = new AdminService();