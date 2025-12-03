import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Brain,
  Zap,
  Shield,
  ArrowRight,
  Info,
  FileText,
  Users,
  Download
} from 'lucide-react';
import UniversalFileUpload from '@/components/upload/UniversalFileUpload';

export default function LandingPage() {
  const features = [
    {
      icon: Brain,
      title: '95%+ Accuracy',
      description: 'State-of-the-art AI models trained on over 100K names for enterprise-grade parsing.'
    },
    {
      icon: Zap,
      title: 'Lightning Fast',
      description: 'Process 1000 names in under 1 minute with our optimized pipeline.'
    },
    {
      icon: Shield,
      title: 'Secure & Compliant',
      description: 'Bank-level encryption with automatic 10-minute data deletion.'
    },
    {
      icon: FileText,
      title: 'Entity Detection',
      description: 'Automatically identify trusts, estates, businesses, and organizations.'
    },
    {
      icon: Users,
      title: 'Gender Detection',
      description: 'Advanced gender prediction based on name patterns and cultural context.'
    },
    {
      icon: Download,
      title: 'Easy Export',
      description: 'Download results in CSV or Excel format with all parsed fields.'
    }
  ];


  return (
    <div className="min-h-screen">
      {/* Hero Section with Prominent Upload */}
      <section className="py-12 px-4">
        <div className="container mx-auto">
          <div className="text-center mb-12">
            <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl xl:text-8xl 2xl:text-[6.8rem] 3xl:text-[7.5rem] leading-none font-black tracking-tight mb-6">
              Name Extraction, Gender Identification.
              <span className="text-primary"> Instantly.</span>
            </h1>

            <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
              Transform messy name data into structured insights. Extract first/last names, identify gender, and detect entity types (person, company, trust) with 95%+ AI-powered accuracy.
            </p>
          </div>

          {/* Prominent Upload Section */}
          <div className="max-w-4xl mx-auto mb-16">
            <div className="bg-muted rounded-2xl p-8 border border-primary/10">
              <div className="text-center mb-6">
                <h2 className="text-2xl font-bold mb-2">
                  Try 5 Parses Free
                </h2>
                <p className="text-muted-foreground">
                  Upload a CSV or Excel file with up to 5 names - no signup required
                </p>
                <div className="mt-4 rounded-lg border-l-4 border-primary bg-gradient-to-r from-primary/10 to-blue-500/5 p-5 text-left">
                  <div className="flex items-start gap-3">
                    <Info className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="font-semibold text-base text-foreground mb-2">
                        Required Column Name
                      </p>
                      <p className="text-sm text-muted-foreground mb-3">
                        Your file must contain one of these column names:
                      </p>
                      <div className="flex flex-wrap gap-2">
                        <code className="bg-primary/10 border border-primary/20 px-3 py-1.5 rounded font-mono text-sm font-semibold text-foreground">name</code>
                        <span className="text-muted-foreground">or</span>
                        <code className="bg-primary/10 border border-primary/20 px-3 py-1.5 rounded font-mono text-sm font-semibold text-foreground">parse_string</code>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              
              <UniversalFileUpload
                showTitle={false}
                compact={true}
              />
            </div>
          </div>

          {/* Call to Action Buttons */}
          <div className="text-center mb-12">
            <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
              <Link to="/auth/register">
                <Button size="lg" variant="prominent" className="px-8">
                  Subscribe Now
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
              <Link to="/pricing">
                <Button size="lg" variant="outline" className="px-8">
                  View Pricing
                </Button>
              </Link>
            </div>

            <p className="text-sm text-muted-foreground">
              Free Anonymous Parsing • No credit card required • Instant results
            </p>
          </div>

          {/* Stats */}
          <div className="bg-muted/50 p-6 sm:p-8 md:p-10 lg:p-12 rounded-2xl border-2 border-primary/10 shadow-lg">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 sm:gap-10 md:gap-12 max-w-4xl mx-auto">
              <div className="text-center md:text-left">
                <div className="text-5xl sm:text-6xl md:text-7xl font-black text-primary mb-2">95%+</div>
                <div className="text-sm sm:text-base font-semibold text-foreground">Accuracy Rate</div>
              </div>
              <div className="text-center md:text-left">
                <div className="text-5xl sm:text-6xl md:text-7xl font-black text-primary mb-2">100K+</div>
                <div className="text-sm sm:text-base font-semibold text-foreground">Names Processed</div>
              </div>
              <div className="text-center md:text-left">
                <div className="text-5xl sm:text-6xl md:text-7xl font-black text-primary mb-2">&lt;1min</div>
                <div className="text-sm sm:text-base font-semibold text-foreground">Per 1000 Names</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 px-4 bg-muted/50">
        <div className="container mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-3">
              Why TidyFrame?
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Professional-grade name parsing for businesses that demand accuracy
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 max-w-6xl mx-auto">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <Card key={index} className="text-center transition-all duration-300 hover:shadow-lg hover:scale-105 hover:border-primary/20">
                  <CardHeader>
                    <div className="w-14 h-14 bg-primary/10 rounded-xl flex items-center justify-center mx-auto mb-4 transition-transform duration-300 group-hover:scale-110">
                      <Icon className="h-7 w-7 text-primary" />
                    </div>
                    <CardTitle className="text-xl">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription>
                      {feature.description}
                    </CardDescription>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </section>


      {/* CTA Section */}
      <section className="py-16 px-4 [background:var(--gradient-brand)] text-white">
        <div className="container mx-auto text-center">
          <h2 className="text-3xl font-bold mb-4">
            Start Processing Names Today
          </h2>
          <p className="text-lg mb-8 opacity-95 max-w-2xl mx-auto">
            Join multiple businesses processing over 100K names monthly with TidyFrame
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-6">
            <Link to="/auth/register">
              <Button size="lg" variant="prominent" className="px-8 shadow-lg">
                Subscribe Now
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
            <Link to="/pricing">
              <Button size="lg" variant="outline" className="px-8 border-white text-white hover:bg-white/10">
                View Pricing
              </Button>
            </Link>
          </div>

          <p className="text-sm opacity-90">
            $80/month • 100,000 parses • Cancel anytime
          </p>
        </div>
      </section>
    </div>
  );
}