import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/contexts/AuthContext';
import { Moon, Sun } from 'lucide-react';
import { useState, useEffect } from 'react';

export default function Navbar() {
  const { user, logout } = useAuth();
  const [isDark, setIsDark] = useState(() => {
    // Initialize from localStorage or system preference
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('theme');
      if (stored) return stored === 'dark';
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return false;
  });

  useEffect(() => {
    // Apply dark mode class to document root
    if (isDark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [isDark]);

  const toggleTheme = () => {
    setIsDark(!isDark);
  };

  return (
    <nav className="sticky top-0 z-sticky border-b border-border bg-background/98 backdrop-blur-lg supports-[backdrop-filter]:bg-background/95 shadow-sm">
      <div className="container mx-auto px-3 sm:px-4">
        <div className="flex h-14 sm:h-16 items-center justify-between gap-2 sm:gap-4">
          {/* Logo */}
          <Link to="/" className="flex items-center flex-shrink-0">
            <img src="/logo-with-name.png" alt="TidyFrame" className="h-28 sm:h-30 md:h-32" />
          </Link>

          {/* Navigation Links */}
          <div className="hidden lg:flex items-center space-x-6 xl:space-x-8">
            <Link to="/" className="px-2 xl:px-3 py-2 text-base font-semibold transition-colors hover:text-primary">
              Home
            </Link>
            <Link to="/pricing" className="px-2 xl:px-3 py-2 text-base font-semibold transition-colors hover:text-primary">
              Pricing
            </Link>
            <Link to={user ? "/dashboard/api-keys" : "/docs"} className="px-2 xl:px-3 py-2 text-base font-semibold transition-colors hover:text-primary">
              API Docs
            </Link>
            <Link to="/contact" className="px-2 xl:px-3 py-2 text-base font-semibold transition-colors hover:text-primary">
              Contact
            </Link>
          </div>

          {/* Theme Toggle & Auth Buttons */}
          <div className="flex items-center gap-2 sm:gap-3 md:gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              className="rounded-full"
              aria-label="Toggle theme"
            >
              {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </Button>
            {user ? (
              <div className="flex items-center gap-2 sm:gap-3 md:gap-4">
                <Link to="/dashboard">
                  <Button variant="outline" size="sm" className="sm:size-default">Dashboard</Button>
                </Link>
                <span className="hidden md:inline text-sm text-muted-foreground truncate max-w-[120px] lg:max-w-[200px]">
                  {user.email}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="sm:size-default text-destructive hover:text-destructive/90 hover:bg-destructive/10"
                  onClick={logout}
                >
                  <span className="hidden sm:inline">Logout</span>
                  <span className="sm:hidden">Out</span>
                </Button>
              </div>
            ) : (
              <div className="flex items-center gap-2 sm:gap-3">
                <Link to="/auth/login" className="hidden sm:inline-block">
                  <Button variant="ghost" size="sm" className="sm:size-default">Sign In</Button>
                </Link>
                <Link to="/auth/register">
                  <Button variant="prominent" size="sm" className="sm:size-default whitespace-nowrap">
                    <span className="hidden sm:inline">Subscribe Now</span>
                    <span className="sm:hidden">Subscribe</span>
                  </Button>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}