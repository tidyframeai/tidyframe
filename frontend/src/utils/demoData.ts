import { ParseResult } from '@/types/processing';

/**
 * Demo data showing various parsing scenarios including fallback cases
 * This demonstrates the warning indicators and quality metrics
 */
export const demoParseResults: ParseResult[] = [
  // High-quality Gemini AI results
  {
    originalText: "John Michael Smith",
    firstName: "John",
    lastName: "Smith", 
    middleInitial: "M",
    entityType: "person",
    gender: "male",
    genderConfidence: 0.95,
    parsingConfidence: 0.98,
    warnings: [],
    parsingMethod: "gemini",
    apiCallSuccess: true
  },
  {
    originalText: "Apple Inc.",
    firstName: undefined,
    lastName: undefined,
    entityType: "company",
    gender: undefined,
    parsingConfidence: 0.99,
    warnings: [],
    parsingMethod: "gemini",
    apiCallSuccess: true
  },
  {
    originalText: "Maria Elena Rodriguez",
    firstName: "Maria",
    lastName: "Rodriguez",
    entityType: "person", 
    gender: "female",
    genderConfidence: 0.92,
    parsingConfidence: 0.96,
    warnings: [],
    parsingMethod: "gemini",
    apiCallSuccess: true
  },
  
  // Fallback parsing results with various confidence levels
  {
    originalText: "smith, j.",
    firstName: "J",
    lastName: "Smith",
    entityType: "person",
    gender: "unknown",
    parsingConfidence: 0.45,
    warnings: ["Gemini API timeout - used regex fallback parsing", "Low confidence due to abbreviated format"],
    parsingMethod: "fallback",
    fallbackReason: "API timeout",
    apiCallSuccess: false
  },
  {
    originalText: "ACME CORP",
    firstName: undefined,
    lastName: undefined,
    entityType: "company",
    gender: undefined,
    parsingConfidence: 0.75,
    warnings: ["API rate limit exceeded - used pattern-based parsing"],
    parsingMethod: "fallback",
    fallbackReason: "Rate limit exceeded",
    apiCallSuccess: false
  },
  {
    originalText: "dr. williams",
    firstName: undefined,
    lastName: "Williams",
    entityType: "person",
    gender: "unknown",
    parsingConfidence: 0.65,
    warnings: ["Gemini API error - fallback parsing used", "Title detected but name parsing incomplete"],
    parsingMethod: "fallback", 
    fallbackReason: "API error",
    apiCallSuccess: false
  },
  
  // Mixed quality results
  {
    originalText: "The Johnson Family Trust",
    firstName: undefined,
    lastName: "Johnson",
    entityType: "trust",
    gender: undefined,
    parsingConfidence: 0.88,
    warnings: [],
    parsingMethod: "gemini",
    apiCallSuccess: true
  },
  {
    originalText: "xyz123 holdings llc",
    firstName: undefined,
    lastName: undefined,
    entityType: "company",
    gender: undefined,
    parsingConfidence: 0.35,
    warnings: ["Low confidence parsing - unusual entity name format", "Fallback regex parsing used"],
    parsingMethod: "fallback",
    fallbackReason: "Low confidence AI result",
    apiCallSuccess: true
  },
  {
    originalText: "Robert J. O'Connor Jr.",
    firstName: "Robert",
    lastName: "O'Connor",
    middleInitial: "J",
    entityType: "person",
    gender: "male", 
    genderConfidence: 0.89,
    parsingConfidence: 0.93,
    warnings: [],
    parsingMethod: "gemini",
    apiCallSuccess: true
  },
  {
    originalText: "unknown entity",
    firstName: undefined,
    lastName: undefined,
    entityType: "unknown",
    gender: undefined,
    parsingConfidence: 0.20,
    warnings: ["Could not determine entity type", "Very low confidence result", "Fallback parsing failed"],
    parsingMethod: "fallback",
    fallbackReason: "Unrecognized format",
    apiCallSuccess: false
  }
];

/**
 * Calculate demo metrics that would show warning indicators
 */
export function getDemoMetrics() {
  const totalRows = demoParseResults.length;
  const geminiResults = demoParseResults.filter(r => r.parsingMethod === 'gemini').length;
  const fallbackResults = demoParseResults.filter(r => r.parsingMethod === 'fallback').length;
  const lowConfidenceResults = demoParseResults.filter(r => r.parsingConfidence < 0.7).length;
  
  return {
    totalRows,
    geminiResults,
    fallbackResults,
    lowConfidenceResults,
    fallbackPercentage: Math.round((fallbackResults / totalRows) * 100),
    avgConfidence: Math.round((demoParseResults.reduce((sum, r) => sum + r.parsingConfidence, 0) / totalRows) * 100)
  };
}