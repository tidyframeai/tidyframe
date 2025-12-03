import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  AlertTriangle,
  Brain,
  Zap,
  BarChart3,
  ChevronDown,
  ChevronUp,
  Info,
  CheckCircle,
  TrendingUp
} from 'lucide-react';
import { ParseResult, ProcessingJob } from '@/types/processing';
import {
  calculateQualityMetrics,
  getQualityRecommendations,
  shouldShowQualityAlert,
  QualityMetrics
} from '@/utils/warningHelpers';
import { MetricCard } from '@/components/shared/MetricCard';
import { ProgressBar } from '@/components/shared/ProgressBar';
import { getQualityScoreColor, getQualityScoreIcon, getQualityScoreLabel, getQualityScoreBadgeVariant } from '@/utils/status';

interface AnalyticsData {
  avg_confidence?: number;
  success_rate?: number;
  entity_stats?: {
    person_count?: number;
    company_count?: number;
    trust_count?: number;
    unknown_count?: number;
    error_count?: number;
  };
  high_confidence_count?: number;
  low_confidence_count?: number;
}

// Helper function to extract quality metrics from job analytics data
function getMetricsFromJob(job: ProcessingJob): QualityMetrics {
  const totalRows = job.totalRows || job.processedRows || 0;
  const geminiSuccessCount = job.geminiSuccessCount || 0;
  const fallbackUsageCount = job.fallbackUsageCount || 0;
  const lowConfidenceCount = job.lowConfidenceCount || 0;
  const qualityScore = typeof job.qualityScore === 'number' ? job.qualityScore * 100 : 0;
  
  // Get analytics from analytics field
  const analytics: AnalyticsData = job.analytics || job.stats || {};
  const avgConfidence = analytics.avg_confidence || 0;
  const successRate = analytics.success_rate ? analytics.success_rate / 100 : 1;
  
  return {
    totalRows,
    geminiSuccessCount,
    fallbackCount: fallbackUsageCount,
    lowConfidenceCount,
    successRate,
    fallbackUsagePercentage: totalRows > 0 ? fallbackUsageCount / totalRows : 0,
    avgConfidence,
    qualityScore: Math.round(qualityScore)
  };
}

interface QualityMetricsPanelProps {
  results: ParseResult[];
  job?: ProcessingJob;
  className?: string;
}

export default function QualityMetricsPanel({ results, job, className = '' }: QualityMetricsPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  // Use job analytics data if available, otherwise calculate from results
  const metrics = job && job.analytics ? 
    getMetricsFromJob(job) : 
    calculateQualityMetrics(results);
  const recommendations = getQualityRecommendations(metrics);
  const alertInfo = shouldShowQualityAlert(metrics);

  if (results.length === 0) {
    return null;
  }

  const QualityIcon = getQualityScoreIcon(metrics.qualityScore);

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Quality Alert */}
      {alertInfo.show && (
        <Alert variant={alertInfo.severity === 'error' ? 'destructive' : 'default'}>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{alertInfo.message}</AlertDescription>
        </Alert>
      )}

      {/* Main Quality Metrics Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Data Quality Report
              </CardTitle>
              <CardDescription>
                Parsing quality and method analysis for {metrics.totalRows.toLocaleString()} processed rows
              </CardDescription>
            </div>
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              {isExpanded ? 'Collapse' : 'Expand'}
            </Button>
          </div>
        </CardHeader>
        
        <CardContent className="space-y-6">
          {/* Quality Score */}
          <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg">
            <div className="flex items-center gap-3">
              <QualityIcon className="h-5 w-5" />
              <div>
                <p className="font-semibold">Overall Quality Score</p>
                <p className="text-sm text-muted-foreground">Combined parsing quality rating</p>
              </div>
            </div>
            <div className="text-right">
              <p className={`text-3xl font-bold ${getQualityScoreColor(metrics.qualityScore)}`}>
                {metrics.qualityScore}%
              </p>
              <Badge variant={getQualityScoreBadgeVariant(metrics.qualityScore)}>
                {getQualityScoreLabel(metrics.qualityScore)}
              </Badge>
            </div>
          </div>

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              value={metrics.geminiSuccessCount}
              label="AI Parsed"
              subtitle={`${Math.round((metrics.geminiSuccessCount / metrics.totalRows) * 100)}%`}
              variant="info"
              icon={Brain}
            />
            <MetricCard
              value={metrics.fallbackCount}
              label="Fallback Used"
              subtitle={`${Math.round(metrics.fallbackUsagePercentage * 100)}%`}
              variant="warning"
              icon={Zap}
            />
            <MetricCard
              value={metrics.totalRows - metrics.lowConfidenceCount}
              label="High Quality"
              subtitle={`${Math.round(metrics.successRate * 100)}%`}
              variant="success"
              icon={CheckCircle}
            />
            <MetricCard
              value={metrics.lowConfidenceCount}
              label="Low Confidence"
              subtitle={`${Math.round((metrics.lowConfidenceCount / metrics.totalRows) * 100)}%`}
              variant="error"
              icon={AlertTriangle}
            />
          </div>

          {/* Average Confidence */}
          <ProgressBar
            value={metrics.avgConfidence * 100}
            max={100}
            showLabel
            label={`Average Confidence: ${Math.round(metrics.avgConfidence * 100)}%`}
            dangerZone={70}
            size="sm"
            variant={
              metrics.avgConfidence * 100 >= 85
                ? 'success'
                : metrics.avgConfidence * 100 >= 70
                ? 'primary'
                : 'warning'
            }
          />

          {/* Expanded Details */}
          {isExpanded && (
            <div className="space-y-4 border-t pt-4">
              {/* API Usage Breakdown */}
              <div className="space-y-2">
                <h4 className="font-semibold flex items-center gap-2">
                  <TrendingUp className="h-4 w-4" />
                  API Usage Breakdown
                </h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="flex justify-between">
                    <span>Gemini API Success:</span>
                    <Badge variant="outline" className="bg-status-info-bg border-status-info-border">
                      {Math.round((metrics.geminiSuccessCount / metrics.totalRows) * 100)}%
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span>Fallback Usage:</span>
                    <Badge variant="outline" className="bg-status-warning-bg border-status-warning-border">
                      {Math.round(metrics.fallbackUsagePercentage * 100)}%
                    </Badge>
                  </div>
                </div>
              </div>

              {/* Cost Analysis */}
              <div className="p-3 bg-muted/50 rounded-lg">
                <h4 className="font-semibold text-sm mb-2">Cost Analysis</h4>
                <p className="text-caption text-muted-foreground">
                  Fallback parsing saved approximately{' '}
                  <span className="font-medium text-status-success">
                    ${(metrics.fallbackCount * 0.001).toFixed(3)}
                  </span>{' '}
                  in API costs ({metrics.fallbackCount} API calls avoided)
                </p>
              </div>

              {/* Recommendations */}
              <div className="space-y-2">
                <h4 className="font-semibold flex items-center gap-2">
                  <Info className="h-4 w-4" />
                  Recommendations
                </h4>
                <div className="space-y-2">
                  {recommendations.map((recommendation, index) => (
                    <div key={index} className="flex items-start gap-2 p-2 bg-muted/50 rounded text-sm">
                      <div className="w-2 h-2 bg-primary rounded-full mt-2 flex-shrink-0" />
                      <p>{recommendation}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}