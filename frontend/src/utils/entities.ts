import { User, Building, Shield, FileText, Users, type LucideIcon } from 'lucide-react';

export type EntityType = 'person' | 'company' | 'corporation' | 'business' | 'trust' | 'foundation' | 'unknown';
export type BadgeVariant = 'default' | 'secondary' | 'outline' | 'destructive';

/**
 * Gets the appropriate icon for an entity type
 *
 * @param entityType - The entity type (person, company, trust, etc.)
 * @returns Lucide icon component
 *
 * @example
 * ```tsx
 * const Icon = getEntityIcon('person');
 * <Icon className="h-4 w-4" />
 * ```
 */
export function getEntityIcon(entityType: string | undefined): LucideIcon {
  if (!entityType) return Users;

  switch (entityType.toLowerCase()) {
    case 'person':
      return User;
    case 'company':
    case 'corporation':
    case 'business':
      return Building;
    case 'trust':
    case 'foundation':
      return Shield;
    case 'unknown':
      return FileText;
    default:
      return Users;
  }
}

/**
 * Gets the appropriate badge variant for an entity type
 *
 * @param entityType - The entity type
 * @returns Badge variant
 *
 * @example
 * ```tsx
 * <Badge variant={getEntityBadgeVariant('person')}>Person</Badge>
 * ```
 */
export function getEntityBadgeVariant(entityType: string | undefined): BadgeVariant {
  if (!entityType) return 'destructive';

  switch (entityType.toLowerCase()) {
    case 'person':
      return 'default';
    case 'company':
    case 'corporation':
    case 'business':
      return 'secondary';
    case 'trust':
    case 'foundation':
      return 'outline';
    case 'unknown':
      return 'destructive';
    default:
      return 'destructive';
  }
}

/**
 * Gets the appropriate color class for an entity type
 *
 * @param entityType - The entity type
 * @returns Tailwind color class using status colors
 *
 * @example
 * ```tsx
 * <div className={getEntityColor('person')}>Person</div>
 * ```
 */
export function getEntityColor(entityType: string | undefined): string {
  if (!entityType) return 'text-muted-foreground';

  switch (entityType.toLowerCase()) {
    case 'person':
      return 'text-status-info';
    case 'company':
    case 'corporation':
    case 'business':
      return 'text-status-success';
    case 'trust':
    case 'foundation':
      return 'text-primary';
    case 'unknown':
      return 'text-status-warning';
    default:
      return 'text-muted-foreground';
  }
}

/**
 * Gets the appropriate background color class for an entity type
 *
 * @param entityType - The entity type
 * @returns Tailwind background color class using status colors
 *
 * @example
 * ```tsx
 * <div className={getEntityBackgroundColor('person')}>Person</div>
 * ```
 */
export function getEntityBackgroundColor(entityType: string | undefined): string {
  if (!entityType) return 'bg-muted/50';

  switch (entityType.toLowerCase()) {
    case 'person':
      return 'bg-status-info-bg border-status-info-border';
    case 'company':
    case 'corporation':
    case 'business':
      return 'bg-status-success-bg border-status-success-border';
    case 'trust':
    case 'foundation':
      return 'bg-primary/10 border-primary/20';
    case 'unknown':
      return 'bg-status-warning-bg border-status-warning-border';
    default:
      return 'bg-muted/50';
  }
}

/**
 * Gets a human-readable label for an entity type
 *
 * @param entityType - The entity type
 * @returns Formatted label
 *
 * @example
 * ```tsx
 * getEntityLabel('person') // "Person"
 * getEntityLabel('unknown') // "Unknown"
 * ```
 */
export function getEntityLabel(entityType: string | undefined): string {
  if (!entityType) return 'Unknown';

  const normalized = entityType.toLowerCase();

  // Capitalize first letter
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

/**
 * Checks if an entity type is valid/known
 *
 * @param entityType - The entity type to check
 * @returns True if the entity type is recognized
 *
 * @example
 * ```tsx
 * isValidEntityType('person') // true
 * isValidEntityType('xyz') // false
 * ```
 */
export function isValidEntityType(entityType: string | undefined): boolean {
  if (!entityType) return false;

  const validTypes = [
    'person',
    'company',
    'corporation',
    'business',
    'trust',
    'foundation',
  ];

  return validTypes.includes(entityType.toLowerCase());
}

/**
 * Gets entity statistics from results
 *
 * @param results - Array of parse results with entity types
 * @returns Object with counts for each entity type
 *
 * @example
 * ```tsx
 * const stats = getEntityStats(results);
 * // { person: 50, company: 30, trust: 10, unknown: 5 }
 * ```
 */
export function getEntityStats(
  results: Array<{ entityType: string }>
): Record<string, number> {
  const stats: Record<string, number> = {
    person: 0,
    company: 0,
    trust: 0,
    unknown: 0,
  };

  results.forEach((result) => {
    const type = result.entityType?.toLowerCase();

    if (type === 'person') {
      stats.person++;
    } else if (type === 'company' || type === 'corporation' || type === 'business') {
      stats.company++;
    } else if (type === 'trust' || type === 'foundation') {
      stats.trust++;
    } else {
      stats.unknown++;
    }
  });

  return stats;
}
