/**
 * Integration Tests for Optimized API Service
 * Tests the enhanced frontend-backend communication patterns
 */

import { optimizedApiService } from '../../frontend/src/services/optimizedApi';
import { enhancedProcessingService } from '../../frontend/src/services/enhancedProcessingService';

// Mock axios for controlled testing
import axios from 'axios';
jest.mock('axios');
const mockedAxios = axios;

describe('Optimized API Integration Tests', () => {
  let mockServer;
  let testFile;

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    
    // Create test file blob
    testFile = new File(['test,data\nJohn,Doe\nJane,Smith'], 'test.csv', {
      type: 'text/csv'
    });

    // Mock localStorage
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: jest.fn(() => 'mock-token'),
        setItem: jest.fn(),
        removeItem: jest.fn(),
      },
      writable: true,
    });
  });

  afterEach(() => {
    optimizedApiService.clearCache();
    enhancedProcessingService.cleanup();
  });

  describe('Request Batching and Caching', () => {
    test('should cache GET requests and serve from cache', async () => {
      const mockResponse = { data: { message: 'success', jobs: [] } };
      mockedAxios.create.mockReturnThis();
      mockedAxios.get.mockResolvedValue(mockResponse);

      // First request
      const result1 = await optimizedApiService.get('/api/jobs', { cache: true });
      
      // Second identical request should use cache
      const result2 = await optimizedApiService.get('/api/jobs', { cache: true });

      expect(result1).toEqual(result2);
      expect(mockedAxios.get).toHaveBeenCalledTimes(1); // Only one actual API call
    });

    test('should invalidate cache on POST requests', async () => {
      const mockGetResponse = { data: { jobs: [] } };
      const mockPostResponse = { data: { job_id: '123' } };
      
      mockedAxios.create.mockReturnThis();
      mockedAxios.get.mockResolvedValue(mockGetResponse);
      mockedAxios.post.mockResolvedValue(mockPostResponse);

      // Cache initial GET
      await optimizedApiService.get('/api/jobs', { cache: true });
      
      // POST should invalidate cache
      await optimizedApiService.post('/api/jobs', { test: 'data' });
      
      // Next GET should make new request
      await optimizedApiService.get('/api/jobs', { cache: true });

      expect(mockedAxios.get).toHaveBeenCalledTimes(2);
      expect(mockedAxios.post).toHaveBeenCalledTimes(1);
    });

    test('should handle request deduplication', async () => {
      const mockResponse = { data: { message: 'success' } };
      mockedAxios.create.mockReturnThis();
      mockedAxios.get.mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve(mockResponse), 100))
      );

      // Make multiple identical requests simultaneously
      const promises = [
        optimizedApiService.get('/api/test'),
        optimizedApiService.get('/api/test'),
        optimizedApiService.get('/api/test')
      ];

      const results = await Promise.all(promises);

      // All should return same result
      expect(results[0]).toEqual(results[1]);
      expect(results[1]).toEqual(results[2]);
      
      // But only one actual API call should be made
      expect(mockedAxios.get).toHaveBeenCalledTimes(1);
    });
  });

  describe('Retry Logic and Error Handling', () => {
    test('should retry failed requests with exponential backoff', async () => {
      mockedAxios.create.mockReturnThis();
      mockedAxios.get
        .mockRejectedValueOnce(new Error('Network error'))
        .mockRejectedValueOnce(new Error('Network error'))
        .mockResolvedValueOnce({ data: { message: 'success' } });

      const result = await optimizedApiService.get('/api/test', {
        retries: { maxRetries: 3, baseDelay: 10 }
      });

      expect(result).toEqual({ message: 'success' });
      expect(mockedAxios.get).toHaveBeenCalledTimes(3);
    });

    test('should not retry client errors (4xx)', async () => {
      const clientError = {
        response: { status: 400, data: { message: 'Bad request' } }
      };
      
      mockedAxios.create.mockReturnThis();
      mockedAxios.get.mockRejectedValue(clientError);

      await expect(optimizedApiService.get('/api/test', {
        retries: { maxRetries: 3 }
      })).rejects.toEqual(clientError);

      expect(mockedAxios.get).toHaveBeenCalledTimes(1);
    });

    test('should handle timeout errors gracefully', async () => {
      const timeoutError = {
        code: 'ECONNABORTED',
        message: 'timeout of 5000ms exceeded'
      };
      
      mockedAxios.create.mockReturnThis();
      mockedAxios.get.mockRejectedValue(timeoutError);

      await expect(optimizedApiService.get('/api/test')).rejects.toEqual(timeoutError);
    });
  });

  describe('File Upload Optimization', () => {
    test('should handle standard file uploads with progress tracking', async () => {
      const mockResponse = { data: { job_id: '123', message: 'Upload successful' } };
      mockedAxios.create.mockReturnThis();
      mockedAxios.post.mockImplementation((url, data, config) => {
        // Simulate progress events
        if (config.onUploadProgress) {
          config.onUploadProgress({ loaded: 50, total: 100 });
          config.onUploadProgress({ loaded: 100, total: 100 });
        }
        return Promise.resolve(mockResponse);
      });

      const progressUpdates = [];
      const result = await enhancedProcessingService.uploadFile(
        testFile,
        (progress) => progressUpdates.push(progress)
      );

      expect(result).toEqual({ job_id: '123', message: 'Upload successful' });
      expect(progressUpdates.length).toBeGreaterThan(0);
      expect(progressUpdates[progressUpdates.length - 1].phase).toBe('processing');
    });

    test('should handle chunked uploads for large files', async () => {
      // Create large test file (>5MB)
      const largeFile = new File([new ArrayBuffer(6 * 1024 * 1024)], 'large.csv', {
        type: 'text/csv'
      });

      const mockChunkResponse = { data: { chunk_id: 'chunk_123' } };
      const mockFinalizeResponse = { data: { job_id: '123' } };
      
      mockedAxios.create.mockReturnThis();
      mockedAxios.post
        .mockResolvedValueOnce(mockChunkResponse) // First chunk
        .mockResolvedValueOnce(mockChunkResponse) // Second chunk
        .mockResolvedValueOnce(mockFinalizeResponse); // Finalize

      const chunkCompletions = [];
      const result = await optimizedApiService.uploadFileChunked('/api/upload', largeFile, {
        chunkSize: 5 * 1024 * 1024, // 5MB chunks
        onChunkComplete: (chunk, total) => chunkCompletions.push({ chunk, total })
      });

      expect(result).toEqual({ job_id: '123' });
      expect(chunkCompletions.length).toBeGreaterThan(0);
      expect(mockedAxios.post).toHaveBeenCalledTimes(3); // 2 chunks + finalize
    });

    test('should validate files before upload', async () => {
      const invalidFile = new File([''], 'empty.csv', { type: 'text/csv' });

      await expect(enhancedProcessingService.uploadFile(invalidFile)).rejects.toThrow('File is empty');
    });

    test('should validate CSV headers', async () => {
      const invalidCsv = new File(['invalid,headers\ndata,here'], 'invalid.csv', {
        type: 'text/csv'
      });

      await expect(enhancedProcessingService.uploadFile(invalidCsv)).rejects.toThrow(/column headers/);
    });
  });

  describe('Job Status Polling Optimization', () => {
    test('should poll job status with adaptive intervals', async (done) => {
      const jobId = 'test-job-123';
      let pollCount = 0;
      
      mockedAxios.create.mockReturnThis();
      mockedAxios.get.mockImplementation(() => {
        pollCount++;
        const status = pollCount < 3 ? 'processing' : 'completed';
        return Promise.resolve({
          data: {
            id: jobId,
            status,
            progress: pollCount * 33,
            filename: 'test.csv'
          }
        });
      });

      let updateCount = 0;
      const cleanup = enhancedProcessingService.startPolling(
        jobId,
        {
          onUpdate: (job) => {
            updateCount++;
            expect(job.id).toBe(jobId);
          },
          onComplete: (job) => {
            expect(job.status).toBe('completed');
            expect(updateCount).toBeGreaterThan(0);
            expect(pollCount).toBe(3);
            cleanup();
            done();
          },
          onError: (error) => {
            cleanup();
            done(error);
          }
        },
        { intervalMs: 10 } // Fast polling for test
      );
    });

    test('should handle polling errors with backoff', async (done) => {
      const jobId = 'test-job-123';
      let attemptCount = 0;
      
      mockedAxios.create.mockReturnThis();
      mockedAxios.get.mockImplementation(() => {
        attemptCount++;
        if (attemptCount < 3) {
          return Promise.reject(new Error('Network error'));
        }
        return Promise.resolve({
          data: {
            id: jobId,
            status: 'completed',
            filename: 'test.csv'
          }
        });
      });

      const cleanup = enhancedProcessingService.startPolling(
        jobId,
        {
          onUpdate: (job) => {
            expect(job.status).toBe('completed');
          },
          onComplete: (job) => {
            expect(attemptCount).toBe(3);
            cleanup();
            done();
          },
          onError: (error) => {
            cleanup();
            done(error);
          }
        },
        { intervalMs: 10, backoffMultiplier: 1.1 }
      );
    });

    test('should cache job status responses', async () => {
      const jobId = 'test-job-123';
      const mockJob = {
        id: jobId,
        status: 'completed',
        filename: 'test.csv'
      };
      
      mockedAxios.create.mockReturnThis();
      mockedAxios.get.mockResolvedValue({ data: mockJob });

      // First call
      const result1 = await enhancedProcessingService.getJobStatus(jobId);
      
      // Second call should use cache
      const result2 = await enhancedProcessingService.getJobStatus(jobId);

      expect(result1).toEqual(result2);
      expect(mockedAxios.get).toHaveBeenCalledTimes(1);
    });
  });

  describe('Batch Operations', () => {
    test('should handle batch job status requests efficiently', async () => {
      const jobIds = ['job1', 'job2', 'job3'];
      const mockJobs = jobIds.map(id => ({
        id,
        status: 'completed',
        filename: `test-${id}.csv`
      }));
      
      mockedAxios.create.mockReturnThis();
      mockedAxios.get.mockImplementation((url) => {
        const jobId = url.split('/').pop();
        const job = mockJobs.find(j => j.id === jobId);
        return Promise.resolve({ data: job });
      });

      const results = await enhancedProcessingService.getBatchJobStatus(jobIds);

      expect(results.size).toBe(3);
      jobIds.forEach(id => {
        expect(results.has(id)).toBe(true);
        expect(results.get(id)?.id).toBe(id);
      });
      
      // Should make parallel requests
      expect(mockedAxios.get).toHaveBeenCalledTimes(3);
    });

    test('should prefetch job data for better UX', async () => {
      const jobIds = ['job1', 'job2'];
      
      mockedAxios.create.mockReturnThis();
      mockedAxios.get.mockResolvedValue({
        data: { id: 'job1', status: 'completed' }
      });

      await enhancedProcessingService.prefetchJobData(jobIds);

      // Should attempt to fetch both jobs
      expect(mockedAxios.get).toHaveBeenCalledTimes(2);
    });
  });

  describe('Download Optimization', () => {
    test('should handle download with progress tracking', async () => {
      const jobId = 'test-job-123';
      const mockBlob = new Blob(['csv,data'], { type: 'text/csv' });
      
      mockedAxios.create.mockReturnThis();
      mockedAxios.get.mockImplementation((url, config) => {
        if (config.onDownloadProgress) {
          config.onDownloadProgress({ loaded: 50, total: 100 });
          config.onDownloadProgress({ loaded: 100, total: 100 });
        }
        return Promise.resolve({ data: mockBlob });
      });

      const progressUpdates = [];
      const result = await enhancedProcessingService.downloadResults(
        jobId,
        (progress) => progressUpdates.push(progress)
      );

      expect(result).toBe(mockBlob);
      expect(progressUpdates.length).toBeGreaterThan(0);
      expect(progressUpdates[progressUpdates.length - 1].percentage).toBe(100);
    });

    test('should handle download errors gracefully', async () => {
      const jobId = 'test-job-123';
      const downloadError = {
        response: { status: 410, data: { message: 'Results expired' } }
      };
      
      mockedAxios.create.mockReturnThis();
      mockedAxios.get.mockRejectedValue(downloadError);

      await expect(enhancedProcessingService.downloadResults(jobId)).rejects.toEqual(downloadError);
    });
  });

  describe('Memory Management and Cleanup', () => {
    test('should provide cache statistics', () => {
      const stats = optimizedApiService.getCacheStats();
      
      expect(stats).toHaveProperty('size');
      expect(stats).toHaveProperty('maxSize');
      expect(stats).toHaveProperty('entries');
      expect(Array.isArray(stats.entries)).toBe(true);
    });

    test('should clear cache on demand', () => {
      optimizedApiService.setCache('test-key', { data: 'test' });
      expect(optimizedApiService.getCacheStats().size).toBeGreaterThan(0);
      
      optimizedApiService.clearCache();
      expect(optimizedApiService.getCacheStats().size).toBe(0);
    });

    test('should cleanup polling on service cleanup', () => {
      const jobId = 'test-job-123';
      
      // Start polling
      enhancedProcessingService.startPolling(
        jobId,
        {
          onUpdate: () => {},
          onComplete: () => {},
          onError: () => {}
        }
      );

      const statsBefore = enhancedProcessingService.getStats();
      expect(statsBefore.activePolling).toBeGreaterThan(0);

      // Cleanup should stop all polling
      enhancedProcessingService.cleanup();
      const statsAfter = enhancedProcessingService.getStats();
      expect(statsAfter.activePolling).toBe(0);
    });
  });

  describe('Error Recovery and Resilience', () => {
    test('should handle network connectivity issues', async () => {
      const networkError = new Error('Network Error');
      networkError.code = 'NETWORK_ERROR';
      
      mockedAxios.create.mockReturnThis();
      mockedAxios.get.mockRejectedValue(networkError);

      await expect(optimizedApiService.get('/api/test')).rejects.toEqual(networkError);
    });

    test('should handle server overload gracefully', async () => {
      const overloadError = {
        response: { status: 503, data: { message: 'Service unavailable' } }
      };
      
      mockedAxios.create.mockReturnThis();
      mockedAxios.get.mockRejectedValue(overloadError);

      await expect(optimizedApiService.get('/api/test')).rejects.toEqual(overloadError);
    });

    test('should provide fallback data when available', async () => {
      const jobId = 'test-job-123';
      const cachedJob = {
        id: jobId,
        status: 'processing',
        filename: 'test.csv'
      };
      
      // First, cache some data
      mockedAxios.create.mockReturnThis();
      mockedAxios.get.mockResolvedValueOnce({ data: cachedJob });
      
      await enhancedProcessingService.getJobStatus(jobId);
      
      // Now simulate server error
      const serverError = {
        response: { status: 500, data: { message: 'Internal error' } }
      };
      mockedAxios.get.mockRejectedValue(serverError);

      // Should return cached data for server errors
      const result = await enhancedProcessingService.getJobStatus(jobId);
      expect(result.id).toBe(jobId);
    });
  });

  describe('Performance Monitoring', () => {
    test('should track response times', async () => {
      mockedAxios.create.mockReturnThis();
      mockedAxios.get.mockImplementation((url, config) => {
        // Simulate response with timing header
        return Promise.resolve({
          data: { message: 'success' },
          headers: { 'x-response-time': '150' }
        });
      });

      const result = await optimizedApiService.get('/api/test');
      expect(result).toEqual({ message: 'success' });
    });

    test('should provide service health check', async () => {
      mockedAxios.create.mockReturnThis();
      mockedAxios.get.mockResolvedValue({
        data: { status: 'healthy' }
      });

      const health = await optimizedApiService.healthCheck();
      expect(health.status).toBe('healthy');
      expect(typeof health.responseTime).toBe('number');
    });
  });
});

describe('Integration Error Scenarios', () => {
  test('should handle authentication token expiry', async () => {
    // Mock expired token scenario
    mockedAxios.create.mockReturnThis();
    mockedAxios.post
      .mockRejectedValueOnce({ response: { status: 401 } })
      .mockResolvedValueOnce({
        data: { access_token: 'new-token', refresh_token: 'new-refresh' }
      });
    mockedAxios.get.mockResolvedValue({ data: { message: 'success' } });

    const result = await optimizedApiService.get('/api/protected');
    expect(result).toEqual({ message: 'success' });
  });

  test('should handle quota exceeded scenarios', async () => {
    const quotaError = {
      response: { 
        status: 403, 
        data: { message: 'Monthly quota exceeded' } 
      }
    };
    
    mockedAxios.create.mockReturnThis();
    mockedAxios.post.mockRejectedValue(quotaError);

    await expect(
      enhancedProcessingService.uploadFile(
        new File(['test'], 'test.csv', { type: 'text/csv' })
      )
    ).rejects.toEqual(quotaError);
  });

  test('should handle file size limit exceeded', async () => {
    const sizeError = {
      response: { 
        status: 413, 
        data: { message: 'File too large' } 
      }
    };
    
    mockedAxios.create.mockReturnThis();
    mockedAxios.post.mockRejectedValue(sizeError);

    const largeFile = new File([new ArrayBuffer(100 * 1024 * 1024)], 'large.csv');
    
    await expect(
      enhancedProcessingService.uploadFile(largeFile)
    ).rejects.toEqual(sizeError);
  });
});

// Performance benchmarks
describe('Performance Tests', () => {
  test('should handle high concurrent request load', async () => {
    mockedAxios.create.mockReturnThis();
    mockedAxios.get.mockResolvedValue({ data: { message: 'success' } });

    const startTime = Date.now();
    const promises = Array.from({ length: 100 }, (_, i) => 
      optimizedApiService.get(`/api/test-${i}`)
    );

    const results = await Promise.all(promises);
    const endTime = Date.now();

    expect(results.length).toBe(100);
    expect(endTime - startTime).toBeLessThan(5000); // Should complete within 5 seconds
  });

  test('should efficiently handle cache operations', () => {
    const startTime = Date.now();
    
    // Fill cache
    for (let i = 0; i < 1000; i++) {
      optimizedApiService.setCache(`key-${i}`, { data: `value-${i}` });
    }
    
    // Read from cache
    for (let i = 0; i < 1000; i++) {
      optimizedApiService.getFromCache(`key-${i}`);
    }
    
    const endTime = Date.now();
    expect(endTime - startTime).toBeLessThan(100); // Should be very fast
  });
});