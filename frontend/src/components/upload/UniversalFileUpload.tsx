import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone, FileRejection } from 'react-dropzone';
import { useAuth } from '@/contexts/AuthContext';
import { processingService } from '@/services/processingService';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Upload,
  FileSpreadsheet,
  AlertCircle,
  X,
  Info,
  Download,
  Users,
  Crown,
  Zap,
  Building,
  Settings
} from 'lucide-react';
import { toast } from 'sonner';
import { generateSampleCSV, downloadCSVFile, validateCSVHeaders } from '@/utils/csvUtils';
import { PLAN_CONFIG, FILE_TYPES, VALIDATION } from '@/config/constants';

interface FileWithPreview extends File {
  preview?: string;
}


interface UniversalFileUploadProps {
  showTitle?: boolean;
  compact?: boolean;
  onUploadSuccess?: (jobId: string) => void;
}

export default function UniversalFileUpload({ 
  showTitle = true, 
  compact = false,
  onUploadSuccess 
}: UniversalFileUploadProps) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');
  const [columnName, setColumnName] = useState('');
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);

  // Prevent browser from navigating when files dropped outside dropzone
  // This is critical UX - dropping files on document navigates away and loses all progress
  useEffect(() => {
    const preventDefaults = (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
    };

    // Prevent default behavior for drag events on the entire document
    document.addEventListener('dragover', preventDefaults);
    document.addEventListener('drop', preventDefaults);

    // Cleanup event listeners on component unmount
    return () => {
      document.removeEventListener('dragover', preventDefaults);
      document.removeEventListener('drop', preventDefaults);
    };
  }, []);

  // Determine user plan and limits
  const getUserLimits = () => {
    if (!user) {
      // Anonymous user
      const config = PLAN_CONFIG.anonymous;
      return {
        maxFileSize: config.maxFileSize,
        maxParses: config.maxParses,
        planName: config.planName,
        planIcon: Info,
        planColor: config.planColor,
        currentUsage: 0
      };
    }

    switch (user.plan) {
      case 'ENTERPRISE':
        return {
          ...PLAN_CONFIG.enterprise,
          planIcon: Building,
          currentUsage: user.parsesThisMonth || 0
        };
      case 'STANDARD':
      default:
        return {
          ...PLAN_CONFIG.standard,
          planIcon: Crown,
          currentUsage: user.parsesThisMonth || 0
        };
    }
  };

  const limits = getUserLimits();
  const PlanIcon = limits.planIcon;

  const acceptedTypes = FILE_TYPES.ACCEPTED;

  const onDrop = useCallback(async (acceptedFiles: File[], rejectedFiles: FileRejection[]) => {
    setError('');

    if (rejectedFiles.length > 0) {
      const rejection = rejectedFiles[0];
      if (rejection.errors.some((e) => e.code === 'file-too-large')) {
        setError(`File is too large. Maximum size is ${limits.maxFileSize / (1024 * 1024)}MB for ${limits.planName} plan.`);
      } else if (rejection.errors.some((e) => e.code === 'file-invalid-type')) {
        setError('Invalid file type. Please upload CSV, Excel, or TXT files.');
      }
      return;
    }

    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      
      // For CSV files, validate column structure
      if (file.type === 'text/csv' || file.name.toLowerCase().endsWith('.csv')) {
        const validationError = await validateFileColumns(file);
        if (validationError) {
          setError(validationError);
          return;
        }
      }
      
      setFiles([Object.assign(file, {
        preview: URL.createObjectURL(file)
      })]);
    }
  }, [limits.maxFileSize, limits.planName]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptedTypes,
    maxSize: limits.maxFileSize,
    maxFiles: 1,
    multiple: false
  });

  const removeFile = () => {
    setFiles([]);
    setError('');
  };

  const handleUpload = async () => {
    if (files.length === 0) {
      setError('Please select a file to upload');
      return;
    }

    const file = files[0];
    setUploading(true);
    setUploadProgress(0);
    setError('');

    try {
      const response = await processingService.uploadFile(
        file,
        (progressEvent) => {
          setUploadProgress(progressEvent.percentage || 0);
        },
        columnName ? { primary_name_column: columnName } : undefined
      );

      toast.success('File uploaded successfully! Processing started.');

      // Call onUploadSuccess callback or navigate
      if (onUploadSuccess) {
        onUploadSuccess(response.jobId);
      } else if (user) {
        // Navigate authenticated users to dashboard
        navigate(`/dashboard/processing?jobId=${response.jobId}`);
      } else {
        // Navigate anonymous users to public status page
        navigate(`/status?jobId=${response.jobId}`);
      }
    } catch (err: unknown) {
      const error = err as Error & { response?: { data?: { message?: string; detail?: string }; status?: number } };
      const errorMsg = error.response?.data?.message || error.response?.data?.detail || 'Upload failed. Please try again.';
      setError(errorMsg);
      
      // Handle quota exceeded specifically
      if (error.response?.status === 403) {
        if (!user) {
          toast.error('Anonymous limit reached. Sign up for more capacity!');
        } else {
          toast.error('Monthly quota exceeded. Upgrade your plan for more capacity.');
        }
      }
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const downloadSampleTemplate = () => {
    const csvContent = generateSampleCSV(true);
    downloadCSVFile(csvContent, 'sample_template.csv');
    toast.success('Sample template downloaded successfully!');
  };

  const validateFileColumns = async (file: File): Promise<string | null> => {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        const validation = validateCSVHeaders(text);
        
        if (!validation.isValid) {
          const detectedHeaders = validation.detectedHeaders?.join(', ') || 'none detected';
          resolve(
            `${validation.message}\n\nDetected headers: ${detectedHeaders}\nRequired: One of: 'name' or 'parse_string'`
          );
        } else {
          resolve(null); // No error
        }
      };
      
      reader.onerror = () => {
        resolve('Unable to read file. Please try again.');
      };
      
      // Only read first 1024 characters to check headers
      const blob = file.slice(0, 1024);
      reader.readAsText(blob);
    });
  };

  const getRemainingParses = () => {
    if (!user) return limits.maxParses; // Anonymous users get full trial
    return Math.max(0, limits.maxParses - limits.currentUsage);
  };

  const getUsagePercentage = () => {
    if (!user) return 0; // Anonymous users start at 0%
    return Math.min(100, (limits.currentUsage / limits.maxParses) * 100);
  };

  return (
    <div className={`space-y-6 ${compact ? 'space-y-4' : ''}`}>
      {showTitle && (
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Upload Files</h1>
          <p className="text-muted-foreground">
            Upload CSV, Excel, or text files for AI-powered name parsing
          </p>
        </div>
      )}

      {/* Plan Status Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={`w-8 h-8 ${limits.planColor} rounded-lg flex items-center justify-center`}>
                <PlanIcon className="h-4 w-4 text-white" />
              </div>
              <span>{limits.planName} Plan</span>
            </div>
            {!user && (
              <Badge variant="secondary" className="text-caption">
                Try Free
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div>
            <h4 className="font-medium">File Size Limit</h4>
            <p className="text-sm text-muted-foreground">
              Up to {limits.maxFileSize / (1024 * 1024)}MB per file
            </p>
          </div>
          <div>
            <h4 className="font-medium">Monthly Parses</h4>
            <p className="text-sm text-muted-foreground">
              {user
                ? `${limits.currentUsage.toLocaleString()} / ${limits.maxParses === 10000000 ? '∞' : limits.maxParses.toLocaleString()}`
                : `${limits.maxParses} trial parses`
              }
            </p>
            {user && (
              <div className="mt-1">
                <div className="w-full bg-gray-200 rounded-full h-1.5">
                  <div
                    className="bg-primary h-1.5 rounded-full transition-all"
                    style={{ width: `${getUsagePercentage()}%` }}
                  ></div>
                </div>
              </div>
            )}
          </div>
          <div>
            <h4 className="font-medium">Remaining</h4>
            <p className="text-sm text-muted-foreground">
              {getRemainingParses().toLocaleString()} parses left
            </p>
            {!user && (
              <p className="text-caption text-primary mt-1">
                Sign up for 100,000/month!
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {!compact && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              File Requirements
            </CardTitle>
            <CardDescription>
              Your file must contain names or addressees for processing
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert>
              <AlertCircle className="h-5 w-5 text-muted-foreground" />
              <AlertDescription>
                <div className="font-semibold text-base mb-2">Required Column Name</div>
                <div className="text-sm text-muted-foreground">
                  Your file must have a column named one of the following:
                </div>
                <ul className="mt-2 ml-4 list-none space-y-1">
                  {VALIDATION.COLUMN_NAMES.map((col) => (
                    <li key={col} className="text-sm">
                      • <code className="bg-muted px-2 py-0.5 rounded text-foreground font-mono text-caption">{col}</code>
                    </li>
                  ))}
                </ul>
                <div className="mt-3 text-caption text-muted-foreground">
                  Note: If multiple matching columns exist, only the first will be used.
                </div>
              </AlertDescription>
            </Alert>
            
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <h4 className="font-medium mb-2">Supported Formats:</h4>
                <ul className="text-sm text-muted-foreground space-y-1">
                  <li>• CSV files (.csv)</li>
                  <li>• Excel files (.xlsx, .xls)</li>
                  <li>• Text files (.txt)</li>
                </ul>
              </div>
              <div>
                <h4 className="font-medium mb-2">Example Data:</h4>
                <div className="text-sm text-muted-foreground space-y-1">
                  <div>John Smith</div>
                  <div>Jane Doe</div>
                  <div>ABC Corporation</div>
                  <div>XYZ Trust</div>
                </div>
              </div>
            </div>

            <Button 
              variant="outline" 
              size="sm"
              onClick={downloadSampleTemplate}
              className="flex items-center gap-2"
            >
              <Download className="h-4 w-4" />
              Download Sample Template
            </Button>
          </CardContent>
        </Card>
      )}

      {/* File Upload Area */}
      <Card>
        <CardHeader className={compact ? 'pb-3' : ''}>
          <CardTitle className={compact ? 'text-xl' : ''}>
            {compact ? 'Try tidyframe.com' : 'Select File'}
          </CardTitle>
          <CardDescription>
            {compact 
              ? `Drop your file here for instant AI name parsing (${!user ? `${limits.maxParses} free anonymous parses` : 'based on your plan'})`
              : 'Drop your file here or click to browse'
            }
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            {...getRootProps()}
            className={`
              border-2 border-dashed rounded-xl text-center cursor-pointer transition-all duration-normal min-h-touch
              ${compact ? 'p-6 sm:p-8' : 'p-8 sm:p-10 md:p-12'}
              ${isDragActive
                ? 'border-primary bg-primary/20 scale-[1.02] shadow-xl'
                : 'border-primary/40 bg-primary/5 hover:border-primary hover:bg-primary/10 hover:shadow-md shadow-sm'
              }
            `}
          >
            <input {...getInputProps()} />
            <div className="flex flex-col items-center gap-4 sm:gap-6">
              <div className={`p-3 sm:p-4 rounded-full ${isDragActive ? 'bg-primary text-white' : 'bg-primary/20'} transition-all`}>
                <Upload className={`${compact ? 'h-8 w-8 sm:h-10 sm:w-10' : 'h-10 w-10 sm:h-12 sm:w-12 md:h-14 md:w-14'} transition-all ${isDragActive ? 'text-white scale-110' : 'text-primary'}`} />
              </div>
              {isDragActive ? (
                <p className={`${compact ? 'text-lg sm:text-xl' : 'text-xl sm:text-2xl'} font-bold text-primary`}>Drop the file here...</p>
              ) : (
                <div>
                  <p className={`${compact ? 'text-lg sm:text-xl' : 'text-xl sm:text-2xl'} font-bold text-primary mb-2`}>
                    Drag and drop your file here
                  </p>
                  <p className="text-sm sm:text-base text-muted-foreground">
                    or click to browse
                  </p>
                  <p className="text-xs sm:text-sm text-muted-foreground mt-2 sm:mt-3 font-medium">
                    Supports CSV, Excel, and TXT • Max {limits.maxFileSize / (1024 * 1024)}MB
                  </p>
                  {compact && !user && (
                    <div className="mt-4 p-3 bg-secondary/20 rounded-lg border-2 border-secondary">
                      <p className="text-base text-primary font-semibold">
                        No signup required • Process {limits.maxParses} names free
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {error && (
            <Alert variant="destructive" className="mt-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* File Preview */}
          {files.length > 0 && (
            <div className="mt-6 space-y-4">
              <h4 className="font-medium">Selected File</h4>
              {files.map((file, index) => (
                <div key={index} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <FileSpreadsheet className="h-8 w-8 text-status-success" />
                    <div>
                      <p className="font-medium">{file.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {formatFileSize(file.size)}
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={removeFile}
                    disabled={uploading}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}

              {/* Upload Progress */}
              {uploading && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Processing...</span>
                    <span>{uploadProgress}%</span>
                  </div>
                  <Progress value={uploadProgress} />
                </div>
              )}

              {/* Column Settings - Only show to authenticated users */}
              {user && (
                <div className="space-y-4">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full flex items-center gap-2"
                    onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
                    type="button"
                  >
                    <Settings className="h-4 w-4" />
                    Column Settings (Optional)
                  </Button>

                  {showAdvancedOptions && (
                    <Card className="border-dashed">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm">Custom Column Name</CardTitle>
                        <CardDescription className="text-caption">
                          Specify the column that contains names to process. Leave blank to use default detection.
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <Label htmlFor="column-name" className="text-sm">Column Name</Label>
                        <Input
                          id="column-name"
                          value={columnName}
                          onChange={(e) => setColumnName(e.target.value)}
                          placeholder="e.g., name, parse_string..."
                          className="mt-1"
                          disabled={uploading}
                        />
                        <p className="text-caption text-muted-foreground mt-1">
                          Default detection looks for: 'name' or 'parse_string'
                        </p>
                      </CardContent>
                    </Card>
                  )}
                </div>
              )}

              {/* Upload Button */}
              <div className="flex gap-2">
                <Button 
                  onClick={handleUpload}
                  disabled={uploading || files.length === 0}
                  className="flex-1"
                  size={compact ? "default" : "lg"}
                  variant="prominent"
                >
                  {uploading ? (
                    <>
                      <Upload className="mr-2 h-4 w-4 animate-pulse" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <Zap className="mr-2 h-4 w-4" />
                      {compact ? 'Process Names' : 'Start AI Processing'}
                    </>
                  )}
                </Button>
                {!compact && (
                  <Button
                    variant="outline"
                    onClick={removeFile}
                    disabled={uploading}
                  >
                    Cancel
                  </Button>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}