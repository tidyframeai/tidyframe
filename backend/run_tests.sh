#!/bin/bash

# Load environment variables
if [ -f "../.env" ]; then
    export $(grep -v '^#' ../.env | xargs)
    echo "✅ Loaded environment variables from ../.env"
else
    echo "❌ ERROR: ../.env file not found"
    exit 1
fi

# Check if GEMINI_API_KEY is set
if [ -z "$GEMINI_API_KEY" ]; then
    echo "❌ ERROR: GEMINI_API_KEY not set"
    exit 1
fi

echo "📊 Running TidyFrame Name Parser Test Suite"
echo "🔑 Using Gemini API Key: ${GEMINI_API_KEY:0:10}..."
echo ""

# Run the test
python3 test_name_parser.py