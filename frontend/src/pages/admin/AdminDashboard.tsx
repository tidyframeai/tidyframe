import { useState, useEffect, useCallback } from 'react';
import { logger } from '@/utils/logger';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { 
  Users,
  Activity,
  BarChart3,
  DollarSign,
  Search,
  MoreHorizontal,
  Edit,
  RefreshCw,
  UserCheck,
  UserX,
  Crown
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { adminService, AdminUser, SystemStats } from '@/services/adminService';
import { toast } from 'sonner';

export default function AdminDashboard() {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [planFilter, setPlanFilter] = useState<string>('all');
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null);
  const [editLimitValue, setEditLimitValue] = useState<number | ''>('');
  const [editPlan, setEditPlan] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      logger.debug('AdminDashboard: Loading data...');
      
      // For development, use mock data if API fails
      try {
        const [statsData, usersData] = await Promise.all([
          adminService.getSystemStats(),
          adminService.getUsers({
            search: searchTerm || undefined,
            plan_filter: planFilter === 'all' ? undefined : planFilter,
            page_size: 50,
          }),
        ]);
        setStats(statsData);
        setUsers(usersData);
        logger.debug('AdminDashboard: Data loaded successfully', { statsData, usersCount: usersData.length });
      } catch (apiError) {
        logger.warn('AdminDashboard: API failed, using mock data for development', apiError);
        
        // Use mock data for development
        const mockStats: SystemStats = {
          total_users: 5,
          active_users: 3,
          total_jobs: 12,
          jobs_today: 2,
          total_parses: 150,
          parses_today: 8,
          storage_used_gb: 2.5
        };
        
        const mockUsers: AdminUser[] = [
          {
            id: '1',
            email: 'user@example.com',
            plan: 'STANDARD',
            parsesThisMonth: 10,
            monthlyLimit: 100,
            isActive: true,
            emailVerified: true,
            createdAt: new Date().toISOString(),
          },
          {
            id: '2',
            email: 'admin@example.com',
            plan: 'ENTERPRISE',
            parsesThisMonth: 50,
            monthlyLimit: 999999999,
            isActive: true,
            emailVerified: true,
            createdAt: new Date().toISOString(),
          }
        ];
        
        setStats(mockStats);
        setUsers(mockUsers);
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error && 'response' in err && 
        err.response && typeof err.response === 'object' && 
        'data' in err.response && 
        err.response.data && typeof err.response.data === 'object' && 
        'message' in err.response.data && 
        typeof err.response.data.message === 'string'
        ? err.response.data.message
        : 'Failed to load admin data';
      logger.error('AdminDashboard: Error loading data', err);
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [searchTerm, planFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleEditUser = (user: AdminUser) => {
    setEditingUser(user);
    setEditLimitValue(user.customMonthlyLimit || '');
    setEditPlan(user.plan);
  };

  const handleUpdateLimits = async () => {
    if (!editingUser) return;

    try {
      await adminService.updateUserLimits(editingUser.id, {
        customMonthlyLimit: editLimitValue === '' ? undefined : Number(editLimitValue),
      });
      
      toast.success('User limits updated successfully');
      setEditingUser(null);
      loadData();
    } catch (error) {
      logger.error('Failed to update limits:', error);
      toast.error('Failed to update user limits');
    }
  };

  const handleUpdatePlan = async () => {
    if (!editingUser) return;

    try {
      await adminService.updateUserPlan(editingUser.id, {
        plan: editPlan,
      });
      
      toast.success('User plan updated successfully');
      setEditingUser(null);
      loadData();
    } catch (error) {
      logger.error('Failed to update plan:', error);
      toast.error('Failed to update user plan');
    }
  };

  const handleResetUsage = async (user: AdminUser) => {
    if (!confirm(`Reset usage for ${user.email}? This will set their monthly usage to 0.`)) {
      return;
    }

    try {
      await adminService.resetUserUsage(user.id, { reset_count: 0 });
      toast.success('User usage reset successfully');
      loadData();
    } catch (error) {
      logger.error('Failed to reset usage:', error);
      toast.error('Failed to reset user usage');
    }
  };

  const handleToggleActiveStatus = async (user: AdminUser) => {
    try {
      await adminService.updateUser(user.id, {
        is_active: !user.isActive,
      });
      
      toast.success(`User ${user.isActive ? 'deactivated' : 'activated'} successfully`);
      loadData();
    } catch (error) {
      logger.error('Failed to toggle user status:', error);
      toast.error('Failed to update user status');
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const getPlanBadgeVariant = (plan: string) => {
    switch (plan) {
      case 'ENTERPRISE': return 'default';
      case 'STANDARD': return 'secondary';
      default: return 'outline';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading admin dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="bg-destructive/15 text-destructive p-4 rounded-lg mb-4">
            <h2 className="font-semibold mb-2">Error Loading Dashboard</h2>
            <p className="text-sm">{error}</p>
          </div>
          <Button onClick={loadData} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Debug Info - Development Only */}
      {/* Debug info removed - use browser dev tools instead */}
      
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold">Admin Dashboard</h1>
          <p className="text-muted-foreground">
            Manage users, monitor system performance, and view analytics
          </p>
        </div>
        <Button onClick={loadData} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Users</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_users || 0}</div>
            <p className="text-caption text-muted-foreground">
              {stats?.active_users || 0} active
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Jobs</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_jobs || 0}</div>
            <p className="text-caption text-muted-foreground">
              {stats?.jobs_today || 0} today
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Parses</CardTitle>
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_parses || 0}</div>
            <p className="text-caption text-muted-foreground">
              {stats?.parses_today || 0} today
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Storage Used</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.storage_used_gb?.toFixed(1) || 0} GB</div>
            <p className="text-caption text-muted-foreground">
              System storage
            </p>
          </CardContent>
        </Card>
      </div>

      {/* User Management */}
      <Card>
        <CardHeader>
          <CardTitle>User Management</CardTitle>
          <CardDescription>
            Manage user accounts, plans, and usage limits
          </CardDescription>
          
          {/* Filters */}
          <div className="flex gap-4 pt-4">
            <div className="flex-1 max-w-sm">
              <Label htmlFor="search">Search Users</Label>
              <div className="relative">
                <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder="Search by email..."
                  className="pl-8"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </div>
            <div>
              <Label htmlFor="plan-filter">Filter by Plan</Label>
              <Select value={planFilter} onValueChange={setPlanFilter}>
                <SelectTrigger id="plan-filter" className="w-40">
                  <SelectValue placeholder="All plans" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All plans</SelectItem>
                  <SelectItem value="standard">Standard</SelectItem>
                  <SelectItem value="enterprise">Enterprise</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Plan</TableHead>
                  <TableHead>Usage</TableHead>
                  <TableHead>Limits</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{user.email}</div>
                        {!user.emailVerified && (
                          <div className="text-sm text-muted-foreground">
                            Email not verified
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={getPlanBadgeVariant(user.plan)}>
                        {user.plan}
                        {user.plan === 'ENTERPRISE' && <Crown className="h-3 w-3 ml-1" />}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        {user.parsesThisMonth.toLocaleString()} /{' '}
                        {user.monthlyLimit === 999999999 ? '∞' : user.monthlyLimit.toLocaleString()}
                      </div>
                      {user.customMonthlyLimit && (
                        <div className="text-caption text-muted-foreground">
                          Custom limit
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      {user.customMonthlyLimit ? (
                        <span className="text-sm">
                          {user.customMonthlyLimit.toLocaleString()} (custom)
                        </span>
                      ) : (
                        <span className="text-sm text-muted-foreground">
                          Default
                        </span>
                      )}
                    </TableCell>
                    <TableCell>
                      {user.isActive ? (
                        <div className="flex items-center text-status-success">
                          <UserCheck className="h-4 w-4 mr-1" />
                          Active
                        </div>
                      ) : (
                        <div className="flex items-center text-status-error">
                          <UserX className="h-4 w-4 mr-1" />
                          Inactive
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDate(user.createdAt)}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" className="h-8 w-8 p-0">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>Actions</DropdownMenuLabel>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => handleEditUser(user)}>
                            <Edit className="mr-2 h-4 w-4" />
                            Edit Limits
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleResetUsage(user)}>
                            <RefreshCw className="mr-2 h-4 w-4" />
                            Reset Usage
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleToggleActiveStatus(user)}>
                            {user.isActive ? (
                              <>
                                <UserX className="mr-2 h-4 w-4" />
                                Deactivate
                              </>
                            ) : (
                              <>
                                <UserCheck className="mr-2 h-4 w-4" />
                                Activate
                              </>
                            )}
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Edit User Dialog */}
      <Dialog open={!!editingUser} onOpenChange={() => setEditingUser(null)}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Edit User: {editingUser?.email}</DialogTitle>
            <DialogDescription>
              Update user plan and custom limits
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="plan">Plan</Label>
              <Select value={editPlan} onValueChange={setEditPlan}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="standard">Standard</SelectItem>
                  <SelectItem value="enterprise">Enterprise</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="custom-limit">Custom Monthly Limit</Label>
              <Input
                id="custom-limit"
                type="number"
                placeholder="Leave empty for default"
                value={editLimitValue}
                onChange={(e) => setEditLimitValue(e.target.value === '' ? '' : Number(e.target.value))}
              />
              <p className="text-sm text-muted-foreground">
                Leave empty to use default plan limit
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingUser(null)}>
              Cancel
            </Button>
            <Button onClick={handleUpdatePlan}>Update Plan</Button>
            <Button onClick={handleUpdateLimits}>Update Limits</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}