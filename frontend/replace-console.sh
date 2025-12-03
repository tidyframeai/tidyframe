#!/bin/bash

# Script to replace console statements with logger calls
# Skip ErrorBoundary.tsx and logger.ts (they need direct console access)

FILES=$(find src -type f \( -name "*.ts" -o -name "*.tsx" \) \
  ! -name "logger.ts" \
  ! -name "ErrorBoundary.tsx" \
  -exec grep -l "console\." {} \;)

for file in $FILES; do
  echo "Processing: $file"

  # Check if file already has logger import
  if ! grep -q "import.*logger.*from.*@/utils/logger" "$file"; then
    # Add logger import after first import statement
    sed -i "/^import /a import { logger } from '@/utils/logger';" "$file" || true
    # Remove duplicate imports if added
    awk '!seen[$0]++' "$file" > "${file}.tmp" && mv "${file}.tmp" "$file"
  fi

  # Replace console.log with logger.debug
  sed -i "s/console\.log(/logger.debug(/g" "$file"

  # Replace console.info with logger.info
  sed -i "s/console\.info(/logger.info(/g" "$file"

  # Replace console.warn with logger.warn
  sed -i "s/console\.warn(/logger.warn(/g" "$file"

  # Replace console.error with logger.error
  sed -i "s/console\.error(/logger.error(/g" "$file"
done

echo "✅ Console replacement complete!"
