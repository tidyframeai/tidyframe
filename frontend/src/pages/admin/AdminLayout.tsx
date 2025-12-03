import { Outlet, Link, useLocation } from 'react-router-dom';
import { logger } from '@/utils/logger';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { 
  Home,
  Users,
  BarChart3,
  Settings,
  LogOut,
  Menu,
  Shield,
  Activity,
  Webhook,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState } from 'react';

const sidebarItems = [
  {
    title: 'Overview',
    href: '/admin',
    icon: Home,
  },
  {
    title: 'User Management',
    href: '/admin/users',
    icon: Users,
  },
  {
    title: 'System Stats',
    href: '/admin/stats',
    icon: BarChart3,
  },
  {
    title: 'Jobs Monitor',
    href: '/admin/jobs',
    icon: Activity,
  },
  {
    title: 'Webhooks',
    href: '/admin/webhooks',
    icon: Webhook,
  },
];

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  
  logger.debug('AdminLayout rendering, user:', user);
  logger.debug('User plan:', user?.plan);

  const handleLogout = async () => {
    await logout();
  };

  // Check if user is admin - for development, allow all authenticated users
  // TODO: Implement proper admin role checking in production
  logger.debug('AdminLayout: User plan check:', user?.plan);
  logger.debug('AdminLayout: NODE_ENV:', process.env.NODE_ENV);
  logger.debug('AdminLayout: import.meta.env.DEV:', import.meta.env.DEV);
  
  // In development mode, allow all authenticated users to access admin
  // In production, only allow enterprise and standard plan users
  const isDevelopment = import.meta.env.DEV || import.meta.env.MODE === 'development';
  const hasValidPlan = user?.plan === 'ENTERPRISE' || user?.plan === 'STANDARD';
  // Also allow if user exists but has no plan (development scenario)
  const isAdmin = isDevelopment || hasValidPlan || (isDevelopment && user && !user.plan);
  
  logger.debug('AdminLayout: Permission check:', { isDevelopment, hasValidPlan, isAdmin });
  
  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Shield className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
          <h1 className="text-2xl font-bold mb-2">Access Denied</h1>
          <p className="text-muted-foreground mb-4">
            You need admin privileges to access this area.
          </p>
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">
              Current plan: {user?.plan || 'unknown'}
            </p>
            <Link to="/dashboard">
              <Button>Go to Dashboard</Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Mobile sidebar toggle */}
      <div className="lg:hidden">
        <Button
          variant="ghost"
          className="fixed top-4 left-4 z-modal"
          onClick={() => setSidebarOpen(!sidebarOpen)}
        >
          <Menu className="h-6 w-6" />
        </Button>
      </div>

      <div className="flex">
        {/* Sidebar */}
        <aside
          className={cn(
            'fixed inset-y-0 left-0 z-sidebar w-64 bg-primary/30 border-r transition-transform duration-slow ease-apple lg:translate-x-0',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full'
          )}
        >
          <div className="flex h-full flex-col">
            {/* Logo */}
            <div className="flex h-16 items-center border-b px-6">
              <Link to="/" className="flex items-center space-x-2">
                <img src="/logo-with-name.png" alt="TidyFrame Admin" className="h-50" />
              </Link>
            </div>

            {/* Navigation */}
            <nav className="flex-1 space-y-2 px-4 py-6">
              {sidebarItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.href || 
                  (item.href === '/admin' && location.pathname === '/admin/dashboard');
                
                return (
                  <Link
                    key={item.href}
                    to={item.href}
                    className={cn(
                      'flex items-center space-x-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-primary/30 text-primary font-semibold border-l-4 border-primary'
                        : 'text-muted-foreground hover:bg-primary/10 hover:text-primary'
                    )}
                    onClick={() => setSidebarOpen(false)}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{item.title}</span>
                  </Link>
                );
              })}
            </nav>

            {/* Back to Dashboard */}
            <div className="px-4 pb-4">
              <Link to="/dashboard">
                <Button variant="outline" className="w-full">
                  <Home className="h-4 w-4 mr-2" />
                  Back to Dashboard
                </Button>
              </Link>
            </div>

            {/* User Menu */}
            <div className="border-t p-4">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="w-full justify-start space-x-2">
                    <Avatar className="h-8 w-8">
                      <AvatarFallback>
                        {user?.fullName?.charAt(0) || user?.email.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex flex-col items-start">
                      <span className="text-sm font-medium">
                        {user?.fullName || user?.email}
                      </span>
                      <span className="text-caption text-muted-foreground">
                        Administrator
                      </span>
                    </div>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel>Admin Account</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem>
                    <Settings className="mr-2 h-4 w-4" />
                    <span>Settings</span>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogout} className="cursor-pointer">
                    <LogOut className="mr-2 h-4 w-4" />
                    <span>Log out</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </aside>

        {/* Main content */}
        <main className="flex-1 lg:ml-64">
          {/* Top bar */}
          <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            <div className="flex h-16 items-center justify-between px-6">
              <div className="lg:hidden" /> {/* Spacer for mobile */}
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                  <Shield className="h-4 w-4" />
                  <span>Admin Panel</span>
                </div>
              </div>
            </div>
          </header>

          {/* Page content */}
          <div className="p-6">
            <Outlet />
          </div>
        </main>
      </div>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-overlay bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
}