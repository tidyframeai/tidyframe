import { Link } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Code2,
  Key,
  Zap,
  Shield,
  ArrowRight,
  Lock,
  FileCode,
  Workflow,
  CheckCircle,
  TrendingUp
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

export default function ApiDocsPage() {
  const { user } = useAuth();

  const features = [
    {
      icon: Code2,
      title: 'RESTful API',
      description: 'Simple, intuitive REST endpoints that integrate seamlessly with any tech stack.'
    },
    {
      icon: Key,
      title: 'Secure Authentication',
      description: 'Industry-standard API key authentication with granular access control.'
    },
    {
      icon: Zap,
      title: 'Lightning Fast',
      description: 'Process 1000 names in under 1 minute with our optimized infrastructure.'
    },
    {
      icon: Shield,
      title: 'Enterprise Security',
      description: 'Bank-level encryption with automatic 10-minute data deletion for compliance.'
    },
    {
      icon: FileCode,
      title: 'Comprehensive Docs',
      description: 'Detailed documentation with code examples in Python, JavaScript, and cURL.'
    },
    {
      icon: Workflow,
      title: 'Batch Processing',
      description: 'Upload entire files for bulk processing or integrate individual name parsing.'
    }
  ];

  const useCases = [
    {
      title: 'CRM Integration',
      description: 'Automatically parse and standardize contact names in your CRM system.',
      icon: TrendingUp
    },
    {
      title: 'Data Cleaning',
      description: 'Clean and standardize messy name data from multiple sources.',
      icon: Workflow
    },
    {
      title: 'Lead Enrichment',
      description: 'Extract structured name data and detect entity types for lead scoring.',
      icon: CheckCircle
    }
  ];

  return (
    <div className="min-h-screen py-12 bg-background">
      <div className="container mx-auto px-4 max-w-6xl">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 bg-primary/10 border border-primary/20 rounded-full px-4 py-2 mb-6">
            <Code2 className="h-4 w-4 text-primary" />
            <span className="text-sm font-semibold text-foreground">API Access Available</span>
          </div>

          <h1 className="text-4xl lg:text-5xl font-bold mb-6">
            Powerful REST API for
            <span className="text-primary"> Name Parsing</span>
          </h1>

          <p className="text-lg text-muted-foreground max-w-3xl mx-auto mb-8">
            Integrate AI-powered name parsing directly into your applications. Process names, detect entities,
            and extract insights programmatically with our simple, fast, and secure API.
          </p>

          {user ? (
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/dashboard/api-keys">
                <Button size="lg" variant="default">
                  <Key className="mr-2 h-5 w-5" />
                  View Full Documentation
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
              <Link to="/pricing">
                <Button size="lg" variant="outline">
                  View Pricing
                </Button>
              </Link>
            </div>
          ) : (
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/auth/register">
                <Button size="lg" variant="default">
                  Sign Up for API Access
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
              <Link to="/auth/login">
                <Button size="lg" variant="outline">
                  <Lock className="mr-2 h-5 w-5" />
                  Login to View Docs
                </Button>
              </Link>
            </div>
          )}
        </div>

        {/* Features Grid */}
        <div className="mb-16">
          <h2 className="text-3xl font-bold text-center mb-12">
            Everything You Need to Build
          </h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <Card key={index} className="border-l-4 border-primary/40 hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4">
                      <Icon className="h-6 w-6 text-primary" />
                    </div>
                    <CardTitle className="text-xl">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="text-base">
                      {feature.description}
                    </CardDescription>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>

        {/* Code Example Teaser */}
        <Card className="mb-16 border-primary/20 bg-gradient-to-r from-primary/5 to-transparent">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-2xl mb-2">Simple API Integration</CardTitle>
                <CardDescription className="text-base">
                  Get started with just a few lines of code
                </CardDescription>
              </div>
              <Badge variant="secondary" className="hidden sm:flex">
                3 Simple Steps
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid md:grid-cols-3 gap-4">
              <div className="flex items-center gap-3 p-4 bg-background border rounded-lg">
                <div className="flex-shrink-0 w-8 h-8 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm font-bold">1</div>
                <span className="text-sm font-medium">Upload your file</span>
              </div>
              <div className="flex items-center gap-3 p-4 bg-background border rounded-lg">
                <div className="flex-shrink-0 w-8 h-8 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm font-bold">2</div>
                <span className="text-sm font-medium">Process names</span>
              </div>
              <div className="flex items-center gap-3 p-4 bg-background border rounded-lg">
                <div className="flex-shrink-0 w-8 h-8 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm font-bold">3</div>
                <span className="text-sm font-medium">Download results</span>
              </div>
            </div>

            <div className="relative">
              <pre className="bg-muted border p-6 rounded-lg overflow-x-auto">
                <code className="text-sm font-mono text-foreground">{`curl -X POST https://tidyframe.com/api/upload \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -F "file=@names.csv"

# Response
{
  "job_id": "abc123...",
  "status": "processing",
  "estimated_time": 30
}`}</code>
              </pre>
              {!user && (
                <div className="absolute inset-0 bg-gradient-to-t from-background via-background/80 to-transparent flex items-end justify-center pb-8">
                  <Link to="/auth/register">
                    <Button size="lg">
                      <Lock className="mr-2 h-5 w-5" />
                      Sign Up to See Full Examples
                    </Button>
                  </Link>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Use Cases */}
        <div className="mb-16">
          <h2 className="text-3xl font-bold text-center mb-12">
            Built for Real-World Use Cases
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            {useCases.map((useCase, index) => {
              const Icon = useCase.icon;
              return (
                <Card key={index} className="text-center hover:shadow-lg transition-shadow">
                  <CardContent className="pt-6">
                    <div className="w-14 h-14 bg-primary/10 rounded-xl flex items-center justify-center mx-auto mb-4">
                      <Icon className="h-7 w-7 text-primary" />
                    </div>
                    <h3 className="text-xl font-semibold mb-3">{useCase.title}</h3>
                    <p className="text-muted-foreground">{useCase.description}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>

        {/* Pricing Teaser */}
        <Card className="mb-16 border-primary/20">
          <CardContent className="p-8">
            <div className="text-center max-w-3xl mx-auto">
              <h2 className="text-3xl font-bold mb-4">
                Simple, Transparent Pricing
              </h2>
              <p className="text-lg text-muted-foreground mb-8">
                <strong className="text-foreground">$80/month</strong> for 100,000 name parses with pay-as-you-go overage.
                Enterprise plans available for unlimited usage.
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link to="/pricing">
                  <Button size="lg" variant="outline">
                    View Full Pricing
                  </Button>
                </Link>
                <Link to="/auth/register">
                  <Button size="lg">
                    Start Free Trial
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </Button>
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Access Documentation CTA */}
        <div className="text-center p-12 bg-gradient-to-r from-primary/10 to-blue-600/10 rounded-lg border border-primary/20">
          <div className="max-w-2xl mx-auto">
            <h2 className="text-3xl font-bold mb-4">
              Ready to Integrate?
            </h2>
            <p className="text-lg text-muted-foreground mb-8">
              {user ? (
                <>
                  Access the full API documentation, create your API keys, and start integrating today.
                </>
              ) : (
                <>
                  Sign up for an account to access comprehensive API documentation with code examples,
                  endpoint references, and integration guides.
                </>
              )}
            </p>
            {user ? (
              <Link to="/dashboard/api-keys">
                <Button size="lg" variant="default">
                  <Key className="mr-2 h-5 w-5" />
                  Access Full Documentation
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
            ) : (
              <div className="flex flex-col sm:flex-row gap-4 justify-center">
                <Link to="/auth/register">
                  <Button size="lg" variant="default">
                    Create Free Account
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </Button>
                </Link>
                <Link to="/auth/login">
                  <Button size="lg" variant="outline">
                    <Lock className="mr-2 h-5 w-5" />
                    Already Have an Account?
                  </Button>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
