import { ParseResult } from '@/types/processing';

export type WarningLevel = 'info' | 'warning' | 'error';
export type ParsingMethod = 'gemini' | 'fallback';

export interface ParsingWarning {
  level: WarningLevel;
  message: string;
  reason?: string;
  confidence?: number;
  method: ParsingMethod;
}

export interface QualityMetrics {
  totalRows: number;
  geminiSuccessCount: number;
  fallbackCount: number;
  lowConfidenceCount: number;
  successRate: number;
  fallbackUsagePercentage: number;
  avgConfidence: number;
  qualityScore: number;
}

/**
 * Determines the parsing method based on confidence score and other indicators
 */
export function getParsingMethod(result: ParseResult): ParsingMethod {
  // Check if result contains fallback indicators
  if (result.warnings?.some(warning => 
    warning.toLowerCase().includes('fallback') ||
    warning.toLowerCase().includes('regex') ||
    warning.toLowerCase().includes('pattern')
  )) {
    return 'fallback';
  }
  
  // Low confidence might indicate fallback was used
  if (result.parsingConfidence < 0.6) {
    return 'fallback';
  }
  
  return 'gemini';
}

/**
 * Generates warning information for a parse result
 */
export function getParsingWarning(result: ParseResult): ParsingWarning | null {
  const method = getParsingMethod(result);
  const confidence = result.parsingConfidence;
  
  if (method === 'fallback') {
    if (confidence < 0.4) {
      return {
        level: 'error',
        method,
        confidence,
        message: 'Low quality fallback parsing',
        reason: 'Gemini API failed, used regex fallback with very low confidence'
      };
    } else if (confidence < 0.7) {
      return {
        level: 'warning',
        method,
        confidence,
        message: 'Fallback parsing used',
        reason: 'Gemini API unavailable, used pattern-based fallback'
      };
    } else {
      return {
        level: 'info',
        method,
        confidence,
        message: 'High-quality fallback parsing',
        reason: 'Fallback parser achieved good results'
      };
    }
  }
  
  // Gemini API but low confidence
  if (method === 'gemini' && confidence < 0.7) {
    return {
      level: 'warning',
      method,
      confidence,
      message: 'Low confidence AI parsing',
      reason: 'Gemini AI had difficulty parsing this text'
    };
  }
  
  return null;
}

/**
 * Gets the appropriate color class for confidence scores
 * Uses semantic status colors for consistent theming
 */
export function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.9) return 'text-status-success';
  if (confidence >= 0.7) return 'text-status-warning';
  if (confidence >= 0.5) return 'text-status-warning';
  return 'text-status-error';
}

/**
 * Gets the appropriate background color class for parsing method
 * Uses semantic status colors for consistent theming
 */
export function getMethodColor(method: ParsingMethod): string {
  return method === 'gemini'
    ? 'bg-status-info-bg text-status-info border-status-info-border'
    : 'bg-status-warning-bg text-status-warning border-status-warning-border';
}

/**
 * Gets the appropriate color class for warning level
 * Uses semantic status colors for consistent theming
 */
export function getWarningColor(level: WarningLevel): string {
  switch (level) {
    case 'info': return 'text-status-info';
    case 'warning': return 'text-status-warning';
    case 'error': return 'text-status-error';
    default: return 'text-muted-foreground';
  }
}

/**
 * Formats fallback reasons into user-friendly messages
 */
export function formatFallbackReason(warning: string): string {
  const lowerWarning = warning.toLowerCase();
  
  if (lowerWarning.includes('api') && lowerWarning.includes('limit')) {
    return 'API rate limit reached - used backup parsing system';
  }
  
  if (lowerWarning.includes('api') && lowerWarning.includes('error')) {
    return 'AI service temporarily unavailable - used pattern-based parsing';
  }
  
  if (lowerWarning.includes('timeout')) {
    return 'AI processing timeout - switched to fast pattern parsing';
  }
  
  if (lowerWarning.includes('fallback') || lowerWarning.includes('regex')) {
    return 'Used pattern-based parsing (backup system)';
  }
  
  if (lowerWarning.includes('low confidence')) {
    return 'AI had difficulty - confidence score below threshold';
  }
  
  return 'Alternative parsing method used';
}

/**
 * Calculates quality metrics for a set of results
 */
export function calculateQualityMetrics(results: ParseResult[]): QualityMetrics {
  if (results.length === 0) {
    return {
      totalRows: 0,
      geminiSuccessCount: 0,
      fallbackCount: 0,
      lowConfidenceCount: 0,
      successRate: 0,
      fallbackUsagePercentage: 0,
      avgConfidence: 0,
      qualityScore: 0
    };
  }
  
  let geminiSuccessCount = 0;
  let fallbackCount = 0;
  let lowConfidenceCount = 0;
  let totalConfidence = 0;
  
  results.forEach(result => {
    const method = getParsingMethod(result);
    const confidence = result.parsingConfidence;
    
    if (method === 'gemini') {
      geminiSuccessCount++;
    } else {
      fallbackCount++;
    }
    
    if (confidence < 0.7) {
      lowConfidenceCount++;
    }
    
    totalConfidence += confidence;
  });
  
  const totalRows = results.length;
  const successRate = (results.length - lowConfidenceCount) / totalRows;
  const fallbackUsagePercentage = fallbackCount / totalRows;
  const avgConfidence = totalConfidence / totalRows;
  
  // Calculate overall quality score (0-100)
  // Factors: API usage (40%), confidence (40%), low warning count (20%)
  const apiScore = (geminiSuccessCount / totalRows) * 0.4;
  const confidenceScore = avgConfidence * 0.4;
  const warningScore = Math.max(0, 1 - (lowConfidenceCount / totalRows)) * 0.2;
  const qualityScore = (apiScore + confidenceScore + warningScore) * 100;
  
  return {
    totalRows,
    geminiSuccessCount,
    fallbackCount,
    lowConfidenceCount,
    successRate,
    fallbackUsagePercentage,
    avgConfidence,
    qualityScore: Math.round(qualityScore)
  };
}

/**
 * Generates quality recommendations based on metrics
 */
export function getQualityRecommendations(metrics: QualityMetrics): string[] {
  const recommendations: string[] = [];
  
  if (metrics.fallbackUsagePercentage > 0.3) {
    recommendations.push('High fallback usage detected. Consider checking your API key and quota limits.');
  }
  
  if (metrics.avgConfidence < 0.7) {
    recommendations.push('Low average confidence. Review and clean your input data for better results.');
  }
  
  if (metrics.lowConfidenceCount > metrics.totalRows * 0.2) {
    recommendations.push('Many low-confidence results. Consider preprocessing your data or using higher quality source text.');
  }
  
  if (metrics.qualityScore < 70) {
    recommendations.push('Overall quality score is low. Review input data quality and API configuration.');
  }
  
  if (recommendations.length === 0) {
    recommendations.push('Great job! Your parsing results show high quality and minimal issues.');
  }
  
  return recommendations;
}

/**
 * Determines if a warning banner should be shown for quality issues
 */
export function shouldShowQualityAlert(metrics: QualityMetrics): { show: boolean; severity: 'warning' | 'error'; message: string } {
  if (metrics.fallbackUsagePercentage > 0.5) {
    return {
      show: true,
      severity: 'error',
      message: `Critical: ${Math.round(metrics.fallbackUsagePercentage * 100)}% of results used fallback parsing. Check your API configuration.`
    };
  }
  
  if (metrics.fallbackUsagePercentage > 0.3 || metrics.qualityScore < 60) {
    return {
      show: true,
      severity: 'warning',
      message: `Quality concern: ${Math.round(metrics.fallbackUsagePercentage * 100)}% fallback usage detected. Review results carefully.`
    };
  }
  
  return { show: false, severity: 'warning', message: '' };
}