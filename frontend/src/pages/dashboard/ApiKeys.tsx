import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ApiDocsContent } from '@/components/docs/ApiDocsContent';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import {
  Key,
  Plus,
  Trash2,
  Copy,
  Eye,
  EyeOff,
  Calendar,
  Activity,
  AlertTriangle
} from 'lucide-react';
import { toast } from 'sonner';
import { apiKeyService } from '@/services/apiKeyService';
import { APIKey, APIKeyCreated } from '@/types/apiKeys';
import { SkeletonCard } from '@/components/shared/SkeletonCard';
import { EmptyState } from '@/components/shared/EmptyState';
import { formatDate, formatDateTime } from '@/utils/format';

export default function ApiKeys() {
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [keyModalOpen, setKeyModalOpen] = useState(false);
  const [newApiKey, setNewApiKey] = useState<APIKeyCreated | null>(null);
  const [createLoading, setCreateLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    expires_days: ''
  });

  useEffect(() => {
    loadApiKeys();
  }, []);

  const loadApiKeys = async () => {
    try {
      setLoading(true);
      const keys = await apiKeyService.listAPIKeys();
      setApiKeys(keys);
    } catch {
      toast.error('Failed to load API keys');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateApiKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      toast.error('Please enter a name for the API key');
      return;
    }

    try {
      setCreateLoading(true);
      const request = {
        name: formData.name.trim(),
        ...(formData.expires_days && { expires_days: parseInt(formData.expires_days) })
      };

      const created = await apiKeyService.createAPIKey(request);
      setNewApiKey(created);
      setCreateModalOpen(false);
      setKeyModalOpen(true);
      setFormData({ name: '', expires_days: '' });
      await loadApiKeys();
      toast.success('API key created successfully');
    } catch {
      toast.error('Failed to create API key');
    } finally {
      setCreateLoading(false);
    }
  };

  const handleDeleteApiKey = async (keyId: string, keyName: string) => {
    try {
      await apiKeyService.deleteAPIKey(keyId);
      await loadApiKeys();
      toast.success(`API key "${keyName}" deleted successfully`);
    } catch {
      toast.error('Failed to delete API key');
    }
  };

  const handleToggleStatus = async (keyId: string, keyName: string) => {
    try {
      await apiKeyService.toggleAPIKeyStatus(keyId);
      await loadApiKeys();
      toast.success(`API key "${keyName}" status updated`);
    } catch {
      toast.error('Failed to update API key status');
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success('Copied to clipboard');
    } catch {
      toast.error('Failed to copy to clipboard');
    }
  };

  const isExpired = (expiresAt?: string) => {
    if (!expiresAt) return false;
    return new Date(expiresAt) < new Date();
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">API Keys</h1>
          <p className="text-muted-foreground">
            Manage your API keys for programmatic access
          </p>
        </div>
        <SkeletonCard variant="table" showHeader rows={3} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">API Keys</h1>
          <p className="text-muted-foreground">
            Manage your API keys for programmatic access
          </p>
        </div>
        
        <Dialog open={createModalOpen} onOpenChange={setCreateModalOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create API Key
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New API Key</DialogTitle>
              <DialogDescription>
                Generate a new API key for programmatic access to your account.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreateApiKey}>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="keyName">Name *</Label>
                  <Input
                    id="keyName"
                    placeholder="e.g., Production API, Development Key"
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="expireDays">Expires in (days)</Label>
                  <Input
                    id="expireDays"
                    type="number"
                    min="1"
                    max="365"
                    placeholder="Leave empty for no expiration"
                    value={formData.expires_days}
                    onChange={(e) => setFormData(prev => ({ ...prev, expires_days: e.target.value }))}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => setCreateModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={createLoading}>
                  {createLoading ? 'Creating...' : 'Create Key'}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* API Key Display Modal */}
      <Dialog open={keyModalOpen} onOpenChange={setKeyModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              API Key Created
            </DialogTitle>
            <DialogDescription>
              Your API key has been generated. Copy it now as it won't be shown again.
            </DialogDescription>
          </DialogHeader>
          {newApiKey && (
            <div className="space-y-4 py-4">
              <div className="p-4 bg-muted rounded-lg">
                <div className="flex items-center justify-between gap-2">
                  <code className="text-sm font-mono break-all flex-1">
                    {newApiKey.api_key}
                  </code>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyToClipboard(newApiKey.api_key)}
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <Alert variant="default" className="bg-status-warning-bg border-status-warning-border">
                <AlertTriangle className="h-5 w-5 text-status-warning" />
                <AlertTitle className="text-status-warning">Important!</AlertTitle>
                <AlertDescription>
                  This is the only time you'll see the full API key. Make sure to copy and store it securely.
                </AlertDescription>
              </Alert>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setKeyModalOpen(false)}>
              I've Saved My Key
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* API Keys Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            Your API Keys
          </CardTitle>
          <CardDescription>
            {apiKeys.length === 0 
              ? "You don't have any API keys yet. Create one to get started."
              : `You have ${apiKeys.length} API key${apiKeys.length !== 1 ? 's' : ''}.`
            }
          </CardDescription>
        </CardHeader>
        <CardContent>
          {apiKeys.length === 0 ? (
            <EmptyState
              icon={Key}
              title="No API Keys"
              description="Create your first API key to start using the TidyFrame API programmatically."
              actionLabel="Create Your First API Key"
              onAction={() => setCreateModalOpen(true)}
              size="lg"
              showBranding
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Key</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Usage</TableHead>
                  <TableHead>Last Used</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Expires</TableHead>
                  <TableHead className="w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {apiKeys.map((key) => (
                  <TableRow key={key.id}>
                    <TableCell className="font-medium">{key.name}</TableCell>
                    <TableCell>
                      <code className="text-sm bg-muted px-2 py-1 rounded">
                        {key.key_hint}
                      </code>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Badge 
                          variant={
                            !key.is_active ? 'destructive' :
                            isExpired(key.expires_at) ? 'destructive' :
                            'default'
                          }
                        >
                          {!key.is_active ? 'Disabled' :
                           isExpired(key.expires_at) ? 'Expired' :
                           'Active'}
                        </Badge>
                        {key.is_active && !isExpired(key.expires_at) && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleToggleStatus(key.id, key.name)}
                          >
                            <EyeOff className="h-4 w-4" />
                          </Button>
                        )}
                        {!key.is_active && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleToggleStatus(key.id, key.name)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Activity className="h-4 w-4 text-muted-foreground" />
                        {key.usage_count.toLocaleString()}
                      </div>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDate(key.last_used_at)}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDateTime(key.created_at)}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Calendar className="h-4 w-4" />
                        {key.expires_at ? formatDate(key.expires_at) : 'Never'}
                      </div>
                    </TableCell>
                    <TableCell>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Delete API Key</AlertDialogTitle>
                            <AlertDialogDescription>
                              Are you sure you want to delete the API key "{key.name}"? 
                              This action cannot be undone and will immediately revoke access.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction 
                              onClick={() => handleDeleteApiKey(key.id, key.name)}
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            >
                              Delete Key
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* API Documentation Section */}
      <div className="mt-12 pt-12 border-t">
        <div className="mb-8">
          <h2 className="text-3xl font-bold mb-3">
            API Documentation
          </h2>
          <p className="text-muted-foreground text-lg">
            Complete reference for integrating tidyframe.com API into your applications
          </p>
        </div>

        <ApiDocsContent />
      </div>
    </div>
  );
}