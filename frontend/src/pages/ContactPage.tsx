import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Mail } from 'lucide-react';

export default function ContactPage() {
  return (
    <div className="min-h-screen py-12">
      <div className="container mx-auto px-4 max-w-3xl">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-hero font-bold mb-6">
            Contact Us
          </h1>
          <p className="text-base text-muted-foreground max-w-2xl mx-auto">
            We're here to help with any questions about TidyFrame.
          </p>
        </div>

        {/* Simple Contact Card */}
        <Card className="mx-auto max-w-2xl">
          <CardHeader className="text-center pb-6">
            <CardTitle className="flex items-center justify-center gap-3 text-2xl">
              <Mail className="h-8 w-8 text-primary" />
              Get in Touch
            </CardTitle>
          </CardHeader>
          <CardContent className="text-center space-y-6 pb-12">
            <p className="text-base text-muted-foreground leading-relaxed">
              For any questions, support, or inquiries, please send an email to{' '}
              <a
                href="mailto:tidyframeai@gmail.com"
                className="text-primary hover:underline font-medium"
              >
                tidyframeai@gmail.com
              </a>
              {' '}and we'll get back to you promptly.
            </p>
            
            <div className="pt-4">
              <a
                href="mailto:tidyframeai@gmail.com"
                className="inline-flex items-center gap-2 px-6 py-3 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors font-medium"
              >
                <Mail className="h-5 w-5" />
                Send Email
              </a>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}