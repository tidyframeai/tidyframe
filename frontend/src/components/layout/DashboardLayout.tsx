import { Outlet, Link, useLocation } from 'react-router-dom';
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
  Upload,
  Activity,
  FileText,
  BarChart3,
  User,
  LogOut,
  Settings,
  Menu,
  Key,
  Shield,
  CreditCard,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState } from 'react';
import { PARSE_LIMITS } from '@/config/constants';

const sidebarItems = [
  {
    title: 'Dashboard',
    href: '/dashboard',
    icon: Home,
  },
  {
    title: 'Upload Files',
    href: '/dashboard/upload',
    icon: Upload,
  },
  {
    title: 'Processing',
    href: '/dashboard/processing',
    icon: Activity,
  },
  {
    title: 'Results',
    href: '/dashboard/results',
    icon: FileText,
  },
  {
    title: 'Analytics',
    href: '/dashboard/analytics',
    icon: BarChart3,
  },
  {
    title: 'API Keys',
    href: '/dashboard/api-keys',
    icon: Key,
  },
  {
    title: 'Billing',
    href: '/dashboard/billing',
    icon: CreditCard,
  },
];

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
  };

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
            'fixed inset-y-0 left-0 z-sidebar w-64 bg-gradient-to-b from-card via-card to-card/95 backdrop-blur-xl border-r border-border/30 transition-transform duration-slow ease-apple lg:translate-x-0 shadow-xl shadow-black/5',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full'
          )}
        >
          <div className="flex h-full flex-col">
            {/* Logo with gradient accent */}
            <div className="flex h-20 items-center border-b border-border/30 px-6 bg-gradient-to-r from-primary/10 via-primary/5 to-secondary/10">
              <Link to="/" className="flex items-center space-x-2 hover:opacity-90 transition-opacity">
                <img src="/logo-with-name.png" alt="TidyFrame" className="h-11 w-auto" />
              </Link>
            </div>

            {/* Navigation */}
            <nav className="flex-1 space-y-2 px-3 py-6">
              {sidebarItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.href;

                return (
                  <Link
                    key={item.href}
                    to={item.href}
                    className={cn(
                      'group flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition-all duration-normal',
                      isActive
                        ? 'bg-gradient-to-r from-primary/20 via-primary/15 to-primary/10 text-primary font-semibold shadow-md shadow-primary/10 ring-1 ring-primary/25'
                        : 'text-muted-foreground hover:bg-gradient-to-r hover:from-accent hover:to-accent/50 hover:text-foreground hover:shadow-sm'
                    )}
                    onClick={() => setSidebarOpen(false)}
                  >
                    <div className={cn(
                      'flex items-center justify-center rounded-lg p-2 transition-all',
                      isActive
                        ? 'bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-md shadow-primary/20'
                        : 'bg-muted/50 text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary'
                    )}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <span className="font-medium">{item.title}</span>
                  </Link>
                );
              })}
              
              {/* Admin Panel Link for Enterprise Users */}
              {user?.plan === 'ENTERPRISE' && (
                <Link
                  to="/admin"
                  className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all text-muted-foreground hover:bg-accent hover:text-foreground border border-dashed border-primary/30 mt-4"
                  onClick={() => setSidebarOpen(false)}
                >
                  <div className="flex items-center justify-center rounded-md p-1.5 bg-primary/10">
                    <Shield className="h-4 w-4 text-primary" />
                  </div>
                  <span>Admin Panel</span>
                </Link>
              )}
            </nav>

            {/* User Menu */}
            <div className="border-t border-border/30 p-3 bg-gradient-to-t from-muted/20 to-transparent">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="w-full justify-start gap-3 h-auto py-3 px-3 hover:bg-gradient-to-r hover:from-accent hover:to-accent/50 rounded-xl transition-all">
                    <Avatar className="h-10 w-10 ring-2 ring-primary/30 shadow-md">
                      <AvatarFallback className="bg-gradient-to-br from-primary to-primary/80 text-primary-foreground font-bold">
                        {user?.fullName?.charAt(0) || user?.email?.charAt(0)?.toUpperCase() || 'U'}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex flex-col items-start min-w-0 flex-1">
                      <span className="text-sm font-semibold truncate w-full text-left text-foreground">
                        {user?.fullName || user?.email || 'User'}
                      </span>
                      <span className="text-xs text-muted-foreground capitalize font-medium">
                        {user?.plan || 'loading'} Plan
                      </span>
                    </div>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel>My Account</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild>
                    <Link to="/dashboard/profile" className="cursor-pointer">
                      <User className="mr-2 h-4 w-4" />
                      <span>Profile</span>
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <Link to="/dashboard/api-keys" className="cursor-pointer">
                      <Key className="mr-2 h-4 w-4" />
                      <span>API Keys</span>
                    </Link>
                  </DropdownMenuItem>
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
          <header className="sticky top-0 z-sticky border-b border-border/30 bg-background/85 backdrop-blur-xl supports-[backdrop-filter]:bg-background/70 shadow-sm">
            <div className="flex h-16 items-center justify-between px-6">
              <div className="lg:hidden" /> {/* Spacer for mobile */}
              <div className="flex items-center gap-4 ml-auto">
                {/* Usage Badge */}
                <div className="flex items-center gap-2.5 px-4 py-2 rounded-xl bg-gradient-to-r from-primary/10 to-secondary/10 border border-primary/20 shadow-sm">
                  <div className="flex items-center justify-center h-6 w-6 rounded-lg bg-gradient-to-br from-primary to-primary/80">
                    <Activity className="h-3.5 w-3.5 text-primary-foreground" />
                  </div>
                  <span className="text-sm font-bold text-foreground">
                    {(user?.parsesThisMonth || 0).toLocaleString()}
                  </span>
                  <span className="text-sm text-muted-foreground font-medium">
                    / {user?.plan === 'ENTERPRISE' ? '∞' : PARSE_LIMITS.STANDARD.toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          </header>

          {/* Page content */}
          <div className="p-6 lg:p-8">
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