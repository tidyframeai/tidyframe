import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { BarChart3, TrendingUp, Users, FileText } from 'lucide-react';

export default function Analytics() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
        <p className="text-muted-foreground">
          Track your usage patterns and parsing performance
        </p>
      </div>

      {/* Coming Soon Notice */}
      <Card>
        <CardContent className="p-12 text-center">
          <BarChart3 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-xl font-semibold mb-2">Analytics Dashboard Coming Soon</h3>
          <p className="text-muted-foreground mb-4">
            We're working on comprehensive analytics to help you understand your data processing patterns
          </p>
          <Badge variant="secondary">In Development</Badge>
        </CardContent>
      </Card>

      {/* Preview of Future Features */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Usage Trends
            </CardTitle>
            <CardDescription>
              Track parsing usage over time
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Visual charts showing your monthly and daily usage patterns
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Entity Breakdown
            </CardTitle>
            <CardDescription>
              Analysis of parsed entities
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Pie charts showing distribution of persons, companies, and trusts
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Accuracy Reports
            </CardTitle>
            <CardDescription>
              Confidence score analytics
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Detailed reports on parsing accuracy and confidence levels
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}