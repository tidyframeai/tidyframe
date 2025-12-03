export interface ProcessingJob {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  filename: string;
  originalFilename?: string;
  fileSize?: number;
  createdAt: string;
  created_at?: string;
  startedAt?: string;
  started_at?: string;
  completedAt?: string;
  completed_at?: string;
  updated_at?: string;
  expiresAt?: string;
  expires_at?: string;
  estimatedCompletionTime?: number;
  estimated_time_remaining?: number;
  
  // Results (when completed)
  totalRows?: number;
  total_names?: number;
  processedRows?: number;
  processed_names?: number;
  successfulParses?: number;
  failedParses?: number;
  successRate?: number;
  
  // Quality metrics from backend
  geminiSuccessCount?: number;
  fallbackUsageCount?: number;
  lowConfidenceCount?: number;
  warningCount?: number;
  qualityScore?: number;
  
  // Analytics (when completed)
  analytics?: {
    entity_stats?: {
      person_count: number;
      company_count: number;
      trust_count: number;
      unknown_count: number;
      error_count: number;
    };
    avg_confidence?: number;
    high_confidence_count?: number;
    medium_confidence_count?: number;
    low_confidence_count?: number;
    successRate?: number;
    processing_statistics?: {
      average_processing_time?: number;
      total_processing_time?: number;
      names_per_second?: number;
      peak_memory_usage?: number;
    };
  };
  
  stats?: {
    entity_stats?: {
      person_count: number;
      company_count: number;
      trust_count: number;
      unknown_count: number;
      error_count: number;
    };
    avg_confidence?: number;
    high_confidence_count?: number;
    medium_confidence_count?: number;
    low_confidence_count?: number;
    success_rate?: number;
    total_processed?: number;
    processing_statistics?: {
      average_processing_time?: number;
      total_processing_time?: number;
      names_per_second?: number;
      peak_memory_usage?: number;
    };
  };

  result?: Record<string, unknown>;
  user_id?: string;
  file_id?: string;
  
  // Error info (when failed)
  errorMessage?: string;
  error?: string;
}

// Backend API response format for individual parse results (snake_case)
export interface ParseResultResponse {
  original_name_text: string;
  first_name?: string;
  last_name?: string;
  entity_type: 'person' | 'company' | 'trust' | 'unknown';
  gender?: 'male' | 'female' | 'unknown';
  gender_confidence?: number;
  parsing_confidence: number;
  parsing_method?: 'gemini' | 'fallback' | 'regex' | 'unknown';
  has_warnings?: boolean;
  warnings?: string;
  gemini_used?: boolean;
  fallback_reason?: string;
}

// Frontend format for ParseResult (camelCase)
export interface ParseResult {
  id?: string;
  firstName?: string;
  lastName?: string;
  middleInitial?: string;
  entityType: 'person' | 'company' | 'trust' | 'unknown';
  gender?: 'male' | 'female' | 'unknown';
  genderConfidence?: number;
  parsingConfidence: number;
  originalText: string;
  hasWarnings?: boolean;
  warnings: string[];
  // Optional: Parsing method indicators for fallback detection
  parsingMethod?: 'gemini' | 'fallback' | 'regex' | 'unknown';
  fallbackReason?: string | null;
  geminiUsed?: boolean;
  apiCallSuccess?: boolean;
}

// Job results API response
export interface JobResultsResponse {
  job_id: string;
  filename: string;
  total_rows: number;
  total_results: number;
  returned_rows: number;
  results: ParseResultResponse[];
}

export interface FileUploadResponse {
  jobId: string;
  message: string;
  estimatedProcessingTime?: number;
}

// JobStatusResponse is just an alias for ProcessingJob since backend returns job status directly
export type JobStatusResponse = ProcessingJob;

export interface JobListResponse {
  jobs: ProcessingJob[];
  total: number;
  page: number;
  page_size: number;
}

export interface UsageStats {
  parsesThisMonth: number;
  monthlyLimit: number;
  remainingParses: number;
  usagePercentage: number;
  daysUntilReset: number;
}

// Backend API response format (snake_case)
export interface UsageStatsResponse {
  parses_this_month: number;
  monthly_limit: number;
  remaining_parses: number;
  usage_percentage: number;
  days_until_reset: number;
}