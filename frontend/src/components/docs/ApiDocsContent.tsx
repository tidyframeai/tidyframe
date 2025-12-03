import { logger } from '@/utils/logger';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Code2,
  Key,
  Upload,
  CheckCircle,
  Download,
  AlertCircle,
  Clock,
  FileText,
  Shield,
  Database,
  Copy
} from 'lucide-react';
import { useState } from 'react';

export function ApiDocsContent() {
  const [copiedText, setCopiedText] = useState<string>('');

  const copyToClipboard = async (text: string, identifier: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedText(identifier);
      setTimeout(() => setCopiedText(''), 2000);
    } catch (err) {
      logger.error('Failed to copy text: ', err);
    }
  };

  const CodeBlock = ({ children, identifier }: { children: string; language?: string; identifier: string }) => (
    <div className="relative">
      <pre className="bg-muted border p-4 rounded-lg overflow-x-auto text-sm font-mono">
        <code className="text-foreground">{children}</code>
      </pre>
      <Button
        variant="ghost"
        size="sm"
        className="absolute top-2 right-2 h-8 w-8 p-0"
        onClick={() => copyToClipboard(children, identifier)}
      >
        {copiedText === identifier ? (
          <CheckCircle className="h-4 w-4 text-foreground" />
        ) : (
          <Copy className="h-4 w-4" />
        )}
      </Button>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Quick Start */}
      <Card className="border-primary/20">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Code2 className="h-5 w-5 text-primary" />
            <CardTitle>Quick Start</CardTitle>
          </div>
          <CardDescription>
            Get started with the tidyframe.com API in minutes
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-3 gap-4 text-sm">
            <div className="flex items-center gap-3 p-3 bg-primary/5 border rounded-lg">
              <div className="flex-shrink-0 w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-caption font-bold">1</div>
              <span>Get your API key from the dashboard</span>
            </div>
            <div className="flex items-center gap-3 p-3 bg-primary/5 border rounded-lg">
              <div className="flex-shrink-0 w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-caption font-bold">2</div>
              <span>Upload your file via API</span>
            </div>
            <div className="flex items-center gap-3 p-3 bg-primary/5 border rounded-lg">
              <div className="flex-shrink-0 w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-caption font-bold">3</div>
              <span>Download processed results</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Content */}
      <Tabs defaultValue="authentication" className="space-y-6">
        <TabsList className="grid w-full grid-cols-6 gap-2">
          <TabsTrigger
            value="authentication"
            className="bg-primary/10 border border-primary/20 data-[state=active]:bg-primary/20 data-[state=active]:border-primary/40 data-[state=active]:font-semibold data-[state=active]:shadow-sm transition-all"
          >
            Authentication
          </TabsTrigger>
          <TabsTrigger
            value="endpoints"
            className="bg-primary/10 border border-primary/20 data-[state=active]:bg-primary/20 data-[state=active]:border-primary/40 data-[state=active]:font-semibold data-[state=active]:shadow-sm transition-all"
          >
            Endpoints
          </TabsTrigger>
          <TabsTrigger
            value="examples"
            className="bg-primary/10 border border-primary/20 data-[state=active]:bg-primary/20 data-[state=active]:border-primary/40 data-[state=active]:font-semibold data-[state=active]:shadow-sm transition-all"
          >
            Examples
          </TabsTrigger>
          <TabsTrigger
            value="responses"
            className="bg-primary/10 border border-primary/20 data-[state=active]:bg-primary/20 data-[state=active]:border-primary/40 data-[state=active]:font-semibold data-[state=active]:shadow-sm transition-all"
          >
            Responses
          </TabsTrigger>
          <TabsTrigger
            value="limits"
            className="bg-primary/10 border border-primary/20 data-[state=active]:bg-primary/20 data-[state=active]:border-primary/40 data-[state=active]:font-semibold data-[state=active]:shadow-sm transition-all"
          >
            Rate Limits
          </TabsTrigger>
          <TabsTrigger
            value="formats"
            className="bg-primary/10 border border-primary/20 data-[state=active]:bg-primary/20 data-[state=active]:border-primary/40 data-[state=active]:font-semibold data-[state=active]:shadow-sm transition-all"
          >
            File Formats
          </TabsTrigger>
        </TabsList>

        {/* Authentication Tab */}
        <TabsContent value="authentication">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Key className="h-5 w-5 text-primary" />
                <CardTitle>Authentication</CardTitle>
              </div>
              <CardDescription>
                All API requests require authentication using your API key
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h3 className="text-xl font-semibold mb-3">Getting Your API Key</h3>
                <div className="bg-muted/50 border p-4 rounded-lg mb-4">
                  <div className="flex items-start gap-3">
                    <Shield className="h-5 w-5 text-primary mt-1" />
                    <div>
                      <p className="text-sm">
                        <strong>Step 1:</strong> Log in to your tidyframe.com dashboard
                      </p>
                      <p className="text-sm">
                        <strong>Step 2:</strong> Navigate to Settings → API Keys
                      </p>
                      <p className="text-sm">
                        <strong>Step 3:</strong> Generate a new API key or copy your existing one
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-xl font-semibold mb-3">Using Your API Key</h3>
                <p className="text-muted-foreground mb-4">
                  Include your API key in the Authorization header of every request:
                </p>
                <CodeBlock identifier="auth-header">
{`Authorization: Bearer YOUR_API_KEY_HERE`}
                </CodeBlock>
              </div>

              <div className="bg-destructive/5 border-destructive/20 p-4 rounded-lg border">
                <div className="flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-destructive mt-1" />
                  <div>
                    <h4 className="font-semibold text-foreground mb-2">Security Note</h4>
                    <p className="text-sm text-muted-foreground">
                      Keep your API key secure and never expose it in client-side code.
                      Use server-side applications or secure environment variables only.
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Endpoints Tab */}
        <TabsContent value="endpoints">
          <div className="space-y-6">
            {/* Upload Endpoint */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Upload className="h-5 w-5 text-foreground" />
                    <CardTitle>Upload File</CardTitle>
                  </div>
                  <Badge variant="secondary">POST</Badge>
                </div>
                <CardDescription>
                  Upload a file for name parsing and processing
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-primary/10 border p-3 rounded-lg">
                  <code className="text-sm font-mono text-foreground">POST /api/upload</code>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">Request Body (multipart/form-data)</h4>
                  <div className="text-sm space-y-1">
                    <p><code>file</code> - The file to upload (required)</p>
                    <p><code>primary_name_column</code> - Name column identifier (optional, auto-detected if not specified)</p>
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">Response</h4>
                  <CodeBlock identifier="upload-response">
{`{
  "job_id": "c3d5ffe0-b8f9-477d-87f5-f8ff88d21dfd",
  "message": "File uploaded successfully. Processing started.",
  "estimated_processing_time": 30
}`}
                  </CodeBlock>
                </div>
              </CardContent>
            </Card>

            {/* Job Status Endpoint */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Clock className="h-5 w-5 text-foreground" />
                    <CardTitle>Get Job Status</CardTitle>
                  </div>
                  <Badge variant="outline">GET</Badge>
                </div>
                <CardDescription>
                  Check the processing status of your uploaded file
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-primary/10 border p-3 rounded-lg">
                  <code className="text-sm font-mono text-foreground">GET /api/jobs/{'{'} job_id {'}'}</code>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">Response</h4>
                  <CodeBlock identifier="status-response">
{`{
  "id": "c3d5ffe0-b8f9-477d-87f5-f8ff88d21dfd",
  "status": "completed",
  "progress": 100,
  "filename": "processed_file.csv",
  "created_at": "2025-09-06T02:19:36.089873Z",
  "started_at": "2025-09-06T02:19:36.153497Z",
  "completed_at": "2025-09-06T02:19:37.618437Z",
  "estimated_completion_time": null,
  "total_rows": null,
  "processed_rows": 4,
  "successful_parses": 4,
  "failed_parses": 0,
  "success_rate": 100.0,
  "error_message": null
}`}
                  </CodeBlock>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">Status Values</h4>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">pending</Badge>
                      <span>Queued for processing</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">processing</Badge>
                      <span>Currently being processed</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="default">completed</Badge>
                      <span>Processing complete</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="destructive">failed</Badge>
                      <span>Processing failed</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Download Results Endpoint */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Download className="h-5 w-5 text-foreground" />
                    <CardTitle>Download Results</CardTitle>
                  </div>
                  <Badge variant="outline">GET</Badge>
                </div>
                <CardDescription>
                  Download the processed results file
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-primary/10 border p-3 rounded-lg">
                  <code className="text-sm font-mono text-foreground">GET /api/jobs/{'{'} job_id {'}'}/download</code>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">Response</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    Returns an Excel file (.xlsx) with processed name data
                  </p>
                  <div className="text-sm">
                    <p><strong>Content-Type:</strong> application/vnd.openxmlformats-officedocument.spreadsheetml.sheet</p>
                    <p><strong>Content-Disposition:</strong> attachment; filename="processed_results.xlsx"</p>
                  </div>
                </div>
              </CardContent>
            </Card>

          </div>
        </TabsContent>

        {/* Examples Tab */}
        <TabsContent value="examples">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Complete Workflow Example</CardTitle>
                <CardDescription>
                  Step-by-step example of uploading a file, checking status, and downloading results
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <h3 className="text-xl font-semibold mb-3">Step 1: Upload File</h3>
                  <CodeBlock identifier="curl-upload">
{`curl -X POST https://tidyframe.com/api/upload \\
  -H "Authorization: Bearer YOUR_API_KEY_HERE" \\
  -F "file=@names.csv" \\
  -F "primary_name_column=full_name"`}
                  </CodeBlock>
                </div>

                <div>
                  <h3 className="text-xl font-semibold mb-3">Step 2: Check Job Status</h3>
                  <CodeBlock identifier="curl-status">
{`curl -X GET https://tidyframe.com/api/jobs/job_123456789 \\
  -H "Authorization: Bearer YOUR_API_KEY_HERE"`}
                  </CodeBlock>
                </div>

                <div>
                  <h3 className="text-xl font-semibold mb-3">Step 3: Download Results (when completed)</h3>
                  <CodeBlock identifier="curl-download">
{`curl -X GET https://tidyframe.com/api/jobs/job_123456789/download \\
  -H "Authorization: Bearer YOUR_API_KEY_HERE" \\
  -o processed_results.xlsx`}
                  </CodeBlock>
                </div>

                <div>
                  <h3 className="text-xl font-semibold mb-3">JavaScript/Node.js Example</h3>
                  <CodeBlock identifier="js-example">
{`const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

async function processFile() {
  const form = new FormData();
  form.append('file', fs.createReadStream('names.csv'));
  form.append('primary_name_column', 'full_name');

  // Upload file
  const uploadResponse = await axios.post(
    'https://tidyframe.com/api/upload',
    form,
    {
      headers: {
        'Authorization': 'Bearer YOUR_API_KEY_HERE',
        ...form.getHeaders()
      }
    }
  );

  const jobId = uploadResponse.data.job_id;
  console.log('Job ID:', jobId);

  // Poll for completion
  let status = 'pending';
  while (status !== 'completed') {
    await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds

    const statusResponse = await axios.get(
      \`https://tidyframe.com/api/jobs/\${jobId}\`,
      {
        headers: { 'Authorization': 'Bearer YOUR_API_KEY_HERE' }
      }
    );

    status = statusResponse.data.status;
    console.log('Status:', status);
  }

  // Download results
  const resultResponse = await axios.get(
    \`https://tidyframe.com/api/jobs/\${jobId}/download\`,
    {
      headers: { 'Authorization': 'Bearer YOUR_API_KEY_HERE' },
      responseType: 'stream'
    }
  );

  resultResponse.data.pipe(fs.createWriteStream('results.xlsx'));
  console.log('Results downloaded!');
}`}
                  </CodeBlock>
                </div>

                <div>
                  <h3 className="text-xl font-semibold mb-3">Python Example</h3>
                  <CodeBlock identifier="python-example">
{`import requests
import time

def process_file():
    # Upload file
    with open('names.csv', 'rb') as f:
        files = {'file': f}
        data = {'primary_name_column': 'full_name'}

        response = requests.post(
            'https://tidyframe.com/api/upload',
            files=files,
            data=data,
            headers={'Authorization': 'Bearer YOUR_API_KEY_HERE'}
        )

    job_id = response.json()['job_id']
    print(f'Job ID: {job_id}')

    # Poll for completion
    while True:
        status_response = requests.get(
            f'https://tidyframe.com/api/jobs/{job_id}',
            headers={'Authorization': 'Bearer YOUR_API_KEY_HERE'}
        )

        status = status_response.json()['status']
        print(f'Status: {status}')

        if status == 'completed':
            break
        elif status == 'failed':
            print('Job failed!')
            return

        time.sleep(5)

    # Download results
    result_response = requests.get(
        f'https://tidyframe.com/api/jobs/{job_id}/download',
        headers={'Authorization': 'Bearer YOUR_API_KEY_HERE'}
    )

    with open('results.xlsx', 'wb') as f:
        f.write(result_response.content)

    print('Results downloaded!')

process_file()`}
                  </CodeBlock>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Responses Tab */}
        <TabsContent value="responses">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Response Format</CardTitle>
                <CardDescription>
                  Understanding the structure of API responses and processed data
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <h3 className="text-xl font-semibold mb-3">Processed Data Fields</h3>
                  <p className="text-muted-foreground mb-4">
                    The downloaded Excel file contains the original data plus these additional columns:
                  </p>

                  <div className="grid gap-4">
                    <div className="border rounded-lg p-4">
                      <h4 className="font-semibold mb-2">Entity Classification</h4>
                      <div className="space-y-2 text-sm">
                        <p><code>entity_type</code> - Type of entity: "person", "company", or "trust"</p>
                      </div>
                    </div>

                    <div className="border rounded-lg p-4">
                      <h4 className="font-semibold mb-2">Person Data (when entity_type = "person")</h4>
                      <div className="space-y-2 text-sm">
                        <p><code>first_name</code> - Extracted first name</p>
                        <p><code>last_name</code> - Extracted last name</p>
                        <p><code>middle_initial</code> - Middle initial or name</p>
                        <p><code>gender</code> - Predicted gender: "Male", "Female", or "Unknown"</p>
                        <p><code>gender_confidence</code> - Confidence score (0.0 to 1.0)</p>
                      </div>
                    </div>

                    <div className="border rounded-lg p-4">
                      <h4 className="font-semibold mb-2">Special Classifications</h4>
                      <div className="space-y-2 text-sm">
                        <p><code>is_agricultural_entity</code> - Boolean indicating agricultural business</p>
                        <p><code>processed_name</code> - Cleaned and standardized version of original name</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-xl font-semibold mb-3">Example Processed Data</h3>
                  <CodeBlock identifier="processed-data">
{`Original Name: "John A. Smith"
├─ entity_type: "person"
├─ first_name: "John"
├─ last_name: "Smith"
├─ middle_initial: "A"
├─ gender: "Male"
├─ gender_confidence: 0.95
├─ is_agricultural_entity: false
└─ processed_name: "John A. Smith"

Original Name: "ABC Corporation Ltd"
├─ entity_type: "company"
├─ first_name: null
├─ last_name: null
├─ middle_initial: null
├─ gender: null
├─ gender_confidence: null
├─ is_agricultural_entity: false
└─ processed_name: "ABC Corporation Ltd"

Original Name: "Smith Family Trust"
├─ entity_type: "trust"
├─ first_name: null
├─ last_name: "Smith"
├─ middle_initial: null
├─ gender: null
├─ gender_confidence: null
├─ is_agricultural_entity: false
└─ processed_name: "Smith Family Trust"`}
                  </CodeBlock>
                </div>

                <div>
                  <h3 className="text-xl font-semibold mb-3">Error Responses</h3>
                  <div className="space-y-4">
                    <div>
                      <h4 className="font-medium mb-2">Authentication Error (401)</h4>
                      <CodeBlock identifier="auth-error">
{`{
  "success": false,
  "error": "Unauthorized",
  "message": "Invalid or missing API key"
}`}
                      </CodeBlock>
                    </div>

                    <div>
                      <h4 className="font-medium mb-2">File Too Large (413)</h4>
                      <CodeBlock identifier="size-error">
{`{
  "success": false,
  "error": "File too large",
  "message": "File size exceeds 200MB limit"
}`}
                      </CodeBlock>
                    </div>

                    <div>
                      <h4 className="font-medium mb-2">Invalid File Format (400)</h4>
                      <CodeBlock identifier="format-error">
{`{
  "success": false,
  "error": "Invalid file format",
  "message": "Supported formats: CSV, XLSX, XLS, TXT"
}`}
                      </CodeBlock>
                    </div>

                    <div>
                      <h4 className="font-medium mb-2">Rate Limit Exceeded (429)</h4>
                      <CodeBlock identifier="rate-error">
{`{
  "success": false,
  "error": "Rate limit exceeded",
  "message": "Too many requests. Try again in 60 seconds.",
  "retry_after": 60
}`}
                      </CodeBlock>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Rate Limits Tab */}
        <TabsContent value="limits">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Rate Limits & Usage Quotas</CardTitle>
                <CardDescription>
                  Understand the limits and quotas for API usage
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="border rounded-lg p-4">
                    <h3 className="text-xl font-semibold mb-3 flex items-center gap-2">
                      <Clock className="h-5 w-5 text-foreground" />
                      API Rate Limits
                    </h3>
                    <div className="space-y-3 text-sm">
                      <div className="flex justify-between">
                        <span>Requests per minute:</span>
                        <Badge>60</Badge>
                      </div>
                      <div className="flex justify-between">
                        <span>Requests per hour:</span>
                        <Badge>1,800</Badge>
                      </div>
                      <div className="flex justify-between">
                        <span>Concurrent uploads:</span>
                        <Badge>3</Badge>
                      </div>
                    </div>
                  </div>

                  <div className="border rounded-lg p-4">
                    <h3 className="text-xl font-semibold mb-3 flex items-center gap-2">
                      <Database className="h-5 w-5 text-foreground" />
                      Monthly Quotas
                    </h3>
                    <div className="space-y-3 text-sm">
                      <div className="flex justify-between">
                        <span>Names processed:</span>
                        <Badge>100,000</Badge>
                      </div>
                      <div className="flex justify-between">
                        <span>Overage rate:</span>
                        <Badge variant="outline">Pay-as-you-go</Badge>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-muted/50 border p-6 rounded-lg">
                  <h3 className="text-xl font-semibold mb-3">How Rate Limiting Works</h3>
                  <div className="space-y-3 text-sm">
                    <p>
                      <strong>Request Limits:</strong> Rate limits are enforced per API key using a sliding window.
                      If you exceed the limit, you'll receive a 429 status code with a <code>retry_after</code> header.
                    </p>
                    <p>
                      <strong>Name Processing:</strong> Each name in your uploaded file counts toward your monthly quota.
                      Large files are processed efficiently, but each individual name record is counted.
                    </p>
                    <p>
                      <strong>Overage Billing:</strong> If you exceed 100,000 names in a month, additional names
                      are automatically billed on a pay-as-you-go basis.
                    </p>
                  </div>
                </div>

                <div>
                  <h3 className="text-xl font-semibold mb-3">Best Practices</h3>
                  <div className="grid gap-4">
                    <div className="flex gap-3 p-4 bg-primary/5 border rounded-lg">
                      <CheckCircle className="h-5 w-5 text-primary mt-1 flex-shrink-0" />
                      <div>
                        <h4 className="font-semibold text-foreground">Batch Processing</h4>
                        <p className="text-sm text-muted-foreground">
                          Upload larger files instead of making many small requests to maximize efficiency.
                        </p>
                      </div>
                    </div>

                    <div className="flex gap-3 p-4 bg-primary/5 border rounded-lg">
                      <CheckCircle className="h-5 w-5 text-primary mt-1 flex-shrink-0" />
                      <div>
                        <h4 className="font-semibold text-foreground">Monitor Usage</h4>
                        <p className="text-sm text-muted-foreground">
                          Use the <code>/api/user/usage</code> endpoint to track your current usage and avoid surprises.
                        </p>
                      </div>
                    </div>

                    <div className="flex gap-3 p-4 bg-primary/5 border rounded-lg">
                      <CheckCircle className="h-5 w-5 text-primary mt-1 flex-shrink-0" />
                      <div>
                        <h4 className="font-semibold text-foreground">Implement Retries</h4>
                        <p className="text-sm text-muted-foreground">
                          Handle rate limits gracefully by implementing exponential backoff for 429 responses.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* File Formats Tab */}
        <TabsContent value="formats">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Supported File Formats</CardTitle>
                <CardDescription>
                  File format requirements and specifications
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <h3 className="text-xl font-semibold flex items-center gap-2">
                      <FileText className="h-5 w-5 text-foreground" />
                      Supported Formats
                    </h3>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between p-3 border rounded-lg">
                        <div>
                          <div className="font-medium">CSV Files</div>
                          <div className="text-sm text-muted-foreground">.csv</div>
                        </div>
                        <Badge variant="default">Recommended</Badge>
                      </div>
                      <div className="flex items-center justify-between p-3 border rounded-lg">
                        <div>
                          <div className="font-medium">Excel Files</div>
                          <div className="text-sm text-muted-foreground">.xlsx, .xls</div>
                        </div>
                        <Badge variant="secondary">Supported</Badge>
                      </div>
                      <div className="flex items-center justify-between p-3 border rounded-lg">
                        <div>
                          <div className="font-medium">Text Files</div>
                          <div className="text-sm text-muted-foreground">.txt</div>
                        </div>
                        <Badge variant="outline">Basic</Badge>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h3 className="text-xl font-semibold">File Requirements</h3>
                    <div className="space-y-3 text-sm">
                      <div className="flex items-start gap-2">
                        <CheckCircle className="h-4 w-4 text-foreground mt-0.5 flex-shrink-0" />
                        <span>Maximum file size: <strong>200MB</strong></span>
                      </div>
                      <div className="flex items-start gap-2">
                        <CheckCircle className="h-4 w-4 text-foreground mt-0.5 flex-shrink-0" />
                        <span>Must contain a column with names</span>
                      </div>
                      <div className="flex items-start gap-2">
                        <CheckCircle className="h-4 w-4 text-foreground mt-0.5 flex-shrink-0" />
                        <span>UTF-8 or automatic encoding detection</span>
                      </div>
                      <div className="flex items-start gap-2">
                        <CheckCircle className="h-4 w-4 text-foreground mt-0.5 flex-shrink-0" />
                        <span>Headers in first row (recommended)</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-xl font-semibold mb-3">Column Identification</h3>
                  <p className="text-muted-foreground mb-4">
                    tidyframe.com automatically detects name columns, but you can specify the column name for better accuracy:
                  </p>

                  <div className="grid md:grid-cols-2 gap-4 mb-4">
                    <div className="p-4 bg-primary/5 rounded-lg border">
                      <h4 className="font-semibold text-foreground mb-2">Auto-detected Column Names</h4>
                      <div className="text-sm text-muted-foreground space-y-1">
                        <p>• "name" (any case)</p>
                        <p>• "parse_string" (any case)</p>
                      </div>
                    </div>

                    <div className="p-4 bg-secondary/50 rounded-lg border">
                      <h4 className="font-semibold text-foreground mb-2">Manual Specification</h4>
                      <div className="text-sm text-muted-foreground">
                        <p>Use the <code>primary_name_column</code> parameter in your upload request to specify a different column name.</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-xl font-semibold mb-3">Sample File Formats</h3>
                  <div className="space-y-4">
                    <div>
                      <h4 className="font-medium mb-2">CSV Format Example</h4>
                      <CodeBlock identifier="csv-example">
{`name,email,phone
"John Smith","john@example.com","555-1234"
"ABC Corporation","contact@abc.com","555-5678"
"Smith Family Trust","trust@example.com","555-9012"
"Dr. Sarah Johnson","sarah.j@example.com","555-3456"

OR with parse_string column:

parse_string,email,phone
"John Smith","john@example.com","555-1234"
"ABC Corporation","contact@abc.com","555-5678"`}
                      </CodeBlock>
                    </div>

                    <div>
                      <h4 className="font-medium mb-2">Text File Format Example</h4>
                      <CodeBlock identifier="txt-example">
{`John Smith
ABC Corporation
Smith Family Trust
Dr. Sarah Johnson`}
                      </CodeBlock>
                    </div>
                  </div>
                </div>

                <div className="bg-muted/50 p-4 rounded-lg border">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="h-5 w-5 text-primary mt-1" />
                    <div>
                      <h4 className="font-semibold text-foreground mb-2">Important Notes</h4>
                      <div className="text-sm text-muted-foreground space-y-1">
                        <p>• Files with special characters or international names are fully supported</p>
                        <p>• Excel files should use the first worksheet for data</p>
                        <p>• Large files may take longer to process but are handled efficiently</p>
                        <p>• Empty rows and columns are automatically ignored</p>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
