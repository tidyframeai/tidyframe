import { Link } from 'react-router-dom';

export default function TestDocsPage() {
  return (
    <div className="min-h-screen py-12">
      <div className="container mx-auto px-4">
        <div className="flex justify-center mb-8">
          <Link to="/">
            <img src="/logo-with-name.png" alt="TidyFrame" className="h-16" />
          </Link>
        </div>
        <h1 className="text-4xl font-bold mb-8 text-center">API Documentation</h1>
        <p className="text-xl text-center">This is a test page to verify routing works.</p>
      </div>
    </div>
  );
}