#!/bin/bash

# Fix custom Tailwind classes in all TypeScript/React files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/frontend/src"

echo "Fixing custom Tailwind classes..."

# Text size replacements
find . -name "*.tsx" -type f -exec sed -i 's/text-hero/text-4xl lg:text-5xl/g' {} \;
find . -name "*.tsx" -type f -exec sed -i 's/text-title-1/text-3xl/g' {} \;
find . -name "*.tsx" -type f -exec sed -i 's/text-title-2/text-2xl/g' {} \;
find . -name "*.tsx" -type f -exec sed -i 's/text-headline/text-xl/g' {} \;
find . -name "*.tsx" -type f -exec sed -i 's/text-subhead/text-lg/g' {} \;
find . -name "*.tsx" -type f -exec sed -i 's/text-body/text-base/g' {} \;
find . -name "*.tsx" -type f -exec sed -i 's/text-callout/text-base/g' {} \;
find . -name "*.tsx" -type f -exec sed -i 's/text-footnote/text-sm/g' {} \;
find . -name "*.tsx" -type f -exec sed -i 's/text-tiny/text-xs/g' {} \;

# Rounded replacements
find . -name "*.tsx" -type f -exec sed -i 's/rounded-card/rounded-lg/g' {} \;
find . -name "*.tsx" -type f -exec sed -i 's/rounded-button/rounded-md/g' {} \;

# Shadow replacements
find . -name "*.tsx" -type f -exec sed -i 's/shadow-1/shadow-sm/g' {} \;
find . -name "*.tsx" -type f -exec sed -i 's/shadow-2/shadow-md/g' {} \;
find . -name "*.tsx" -type f -exec sed -i 's/shadow-3/shadow-lg/g' {} \;
find . -name "*.tsx" -type f -exec sed -i 's/shadow-modal/shadow-xl/g' {} \;

echo "✓ Fixed all custom Tailwind classes"