import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import { AuthProvider } from './contexts/AuthContext';
import { SitePasswordProvider } from './contexts/SitePasswordContext';
import { SitePasswordGate } from './components/auth/SitePasswordGate';
import { ErrorBoundary } from './components/ErrorBoundary';
import { Toaster } from 'sonner';

// Public pages - Load upfront for fast initial render
import LandingPage from './pages/LandingPage';
import PricingPage from './pages/PricingPage';

// Lazy loaded pages for code splitting
// Auth pages
const LoginPage = lazy(() => import('./pages/auth/LoginPage'));
const RegisterPage = lazy(() => import('./pages/auth/RegisterPage'));
const PasswordResetPage = lazy(() => import('./pages/auth/PasswordResetPage'));
const EmailVerificationPage = lazy(() => import('./pages/auth/EmailVerificationPage'));

// Contact & Docs
const ContactPage = lazy(() => import('./pages/ContactPage'));
const ApiDocsPage = lazy(() => import('./pages/ApiDocsPage'));

// Payment pages
const PaymentSuccessPage = lazy(() => import('./pages/payment/PaymentSuccessPage'));
const PaymentCancelledPage = lazy(() => import('./pages/payment/PaymentCancelledPage'));

// Legal pages
const TermsOfServicePage = lazy(() => import('./pages/legal/TermsOfServicePage'));
const PrivacyPolicyPage = lazy(() => import('./pages/legal/PrivacyPolicyPage'));

// Dashboard pages
import DashboardLayout from './components/layout/DashboardLayout';
const DashboardHome = lazy(() => import('./pages/dashboard/DashboardHome'));
const FileUpload = lazy(() => import('./pages/dashboard/FileUpload'));
const ProcessingStatus = lazy(() => import('./pages/dashboard/ProcessingStatus'));
const Results = lazy(() => import('./pages/dashboard/Results'));
const Analytics = lazy(() => import('./pages/dashboard/Analytics'));
const Profile = lazy(() => import('./pages/dashboard/Profile'));
const ApiKeys = lazy(() => import('./pages/dashboard/ApiKeys'));
const Billing = lazy(() => import('./pages/dashboard/Billing'));

// Admin pages
const AdminLayout = lazy(() => import('./pages/admin/AdminLayout'));
const AdminDashboard = lazy(() => import('./pages/admin/AdminDashboard'));
const AdminDashboardTest = lazy(() => import('./pages/admin/AdminDashboardTest'));

// Layout components
import PublicLayout from './components/layout/PublicLayout';
import ProtectedRoute from './components/auth/ProtectedRoute';

// Loading component for Suspense
const LoadingFallback = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="animate-pulse text-muted-foreground">Loading...</div>
  </div>
);

function App() {
  return (
    <SitePasswordProvider>
      <SitePasswordGate>
        <AuthProvider>
          <Router>
            <div className="min-h-screen bg-background relative">
              <div className="relative">
            <Routes>
            {/* Public routes */}
            <Route path="/" element={<PublicLayout />}>
              <Route index element={<LandingPage />} />
              <Route path="pricing" element={<PricingPage />} />
              <Route path="contact" element={
                <Suspense fallback={<LoadingFallback />}>
                  <ContactPage />
                </Suspense>
              } />
              <Route path="docs" element={
                <Suspense fallback={<LoadingFallback />}>
                  <ApiDocsPage />
                </Suspense>
              } />
            </Route>

            {/* Auth routes with navbar */}
            <Route path="/auth" element={<PublicLayout />}>
              <Route path="login" element={
                <Suspense fallback={<LoadingFallback />}>
                  <LoginPage />
                </Suspense>
              } />
              <Route path="register" element={
                <Suspense fallback={<LoadingFallback />}>
                  <RegisterPage />
                </Suspense>
              } />
              <Route path="reset-password" element={
                <Suspense fallback={<LoadingFallback />}>
                  <PasswordResetPage />
                </Suspense>
              } />
              <Route path="verify-email" element={
                <Suspense fallback={<LoadingFallback />}>
                  <EmailVerificationPage />
                </Suspense>
              } />
            </Route>

            {/* Payment routes without navbar (clean experience) */}
            <Route path="/payment">
              <Route path="success" element={
                <Suspense fallback={<LoadingFallback />}>
                  <PaymentSuccessPage />
                </Suspense>
              } />
              <Route path="cancelled" element={
                <Suspense fallback={<LoadingFallback />}>
                  <PaymentCancelledPage />
                </Suspense>
              } />
            </Route>

            {/* Legal routes with navbar */}
            <Route path="/legal" element={<PublicLayout />}>
              <Route path="terms-of-service" element={
                <Suspense fallback={<LoadingFallback />}>
                  <TermsOfServicePage />
                </Suspense>
              } />
              <Route path="privacy-policy" element={
                <Suspense fallback={<LoadingFallback />}>
                  <PrivacyPolicyPage />
                </Suspense>
              } />
            </Route>

            {/* Public status route for anonymous job tracking */}
            <Route path="/status" element={<PublicLayout />}>
              <Route index element={
                <Suspense fallback={<LoadingFallback />}>
                  <ProcessingStatus />
                </Suspense>
              } />
            </Route>

            {/* Protected dashboard routes */}
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={
                <Suspense fallback={<LoadingFallback />}>
                  <DashboardHome />
                </Suspense>
              } />
              <Route path="upload" element={
                <Suspense fallback={<LoadingFallback />}>
                  <FileUpload />
                </Suspense>
              } />
              <Route path="processing" element={
                <Suspense fallback={<LoadingFallback />}>
                  <ProcessingStatus />
                </Suspense>
              } />
              <Route path="results" element={
                <Suspense fallback={<LoadingFallback />}>
                  <Results />
                </Suspense>
              } />
              <Route path="analytics" element={
                <Suspense fallback={<LoadingFallback />}>
                  <Analytics />
                </Suspense>
              } />
              <Route path="profile" element={
                <Suspense fallback={<LoadingFallback />}>
                  <Profile />
                </Suspense>
              } />
              <Route path="api-keys" element={
                <Suspense fallback={<LoadingFallback />}>
                  <ApiKeys />
                </Suspense>
              } />
              <Route path="billing" element={
                <Suspense fallback={<LoadingFallback />}>
                  <Billing />
                </Suspense>
              } />
            </Route>

            {/* Protected admin routes */}
            <Route
              path="/admin"
              element={
                <ErrorBoundary>
                  <ProtectedRoute>
                    <Suspense fallback={<LoadingFallback />}>
                      <AdminLayout />
                    </Suspense>
                  </ProtectedRoute>
                </ErrorBoundary>
              }
            >
              <Route index element={
                <Suspense fallback={<LoadingFallback />}>
                  <AdminDashboard />
                </Suspense>
              } />
              <Route path="dashboard" element={
                <Suspense fallback={<LoadingFallback />}>
                  <AdminDashboard />
                </Suspense>
              } />
              <Route path="users" element={
                <Suspense fallback={<LoadingFallback />}>
                  <AdminDashboard />
                </Suspense>
              } />
              <Route path="stats" element={
                <Suspense fallback={<LoadingFallback />}>
                  <AdminDashboard />
                </Suspense>
              } />
              <Route path="jobs" element={
                <Suspense fallback={<LoadingFallback />}>
                  <AdminDashboard />
                </Suspense>
              } />
              <Route path="webhooks" element={
                <Suspense fallback={<LoadingFallback />}>
                  <AdminDashboard />
                </Suspense>
              } />
              <Route path="test" element={
                <Suspense fallback={<LoadingFallback />}>
                  <AdminDashboardTest />
                </Suspense>
              } />
            </Route>
          </Routes>
          <Toaster position="top-right" richColors />
              </div>
            </div>
          </Router>
        </AuthProvider>
      </SitePasswordGate>
    </SitePasswordProvider>
  );
}

export default App;