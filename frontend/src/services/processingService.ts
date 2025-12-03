import { apiService } from './api';
import { ProcessingJob, FileUploadResponse, JobStatusResponse, JobListResponse, UsageStats, ParseResultResponse } from '@/types/processing';

class ProcessingService {
  async uploadFile(
    file: File,
    onUploadProgress?: (progressEvent: { loaded: number; total?: number; percentage: number; phase?: 'uploading' | 'processing' }) => void,
    config?: { primary_name_column?: string }
  ): Promise<FileUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    // Add config as JSON if provided
    if (config) {
      formData.append('config', JSON.stringify(config));
    }
    
    const response = await apiService.getAxiosInstance().post('/api/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: onUploadProgress ? (progressEvent) => {
        const percentage = progressEvent.total 
          ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
          : 0;
        
        onUploadProgress({
          loaded: progressEvent.loaded,
          total: progressEvent.total,
          percentage,
          phase: progressEvent.loaded === progressEvent.total ? 'processing' : 'uploading'
        });
      } : undefined,
    });
    
    return response.data;
  }

  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    return await apiService.get<JobStatusResponse>(`/api/jobs/${jobId}`);
  }

  async getJobs(): Promise<ProcessingJob[]> {
    const response = await apiService.get<JobListResponse>('/api/jobs');
    return response.jobs;
  }

  async deleteJob(jobId: string): Promise<void> {
    await apiService.delete(`/api/jobs/${jobId}`);
  }

  async getJobResults(jobId: string, limit: number = 100): Promise<{
    job_id: string;
    filename: string;
    total_rows: number;
    returned_rows: number;
    results: ParseResultResponse[];
  }> {
    return await apiService.get(`/api/jobs/${jobId}/results?limit=${limit}`);
  }

  async downloadResults(jobId: string): Promise<Blob> {
    const response = await apiService.getAxiosInstance().get(`/api/jobs/${jobId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  }

  async getUserUsage(): Promise<UsageStats> {
    // Use Stripe-integrated endpoint for accurate billing state
    // This ensures dashboard reflects payment status immediately after checkout
    return await apiService.get<UsageStats>('/api/billing/usage');
  }

  // Polling for job status updates
  pollJobStatus(
    jobId: string,
    onUpdate: (job: ProcessingJob) => void,
    onComplete: (job: ProcessingJob) => void,
    onError: (error: Error) => void,
    intervalMs: number = 2000
  ): () => void {
    const poll = async () => {
      try {
        const job = await this.getJobStatus(jobId);
        
        onUpdate(job);

        if (job.status === 'completed' || job.status === 'failed') {
          clearInterval(intervalId);
          onComplete(job);
        }
      } catch (error) {
        clearInterval(intervalId);
        onError(error as Error);
      }
    };

    const intervalId = setInterval(poll, intervalMs);
    
    // Initial poll
    poll();

    // Return cleanup function
    return () => clearInterval(intervalId);
  }
}

export const processingService = new ProcessingService();