#!/bin/bash
# Push CI/CD dependency fixes

set -e

echo "🔧 Pushing CI/CD dependency fixes..."
echo ""
echo "Fixes:"
echo "  ✓ textual 0.90.1 → 0.89.1 (correct version)"
echo "  ✓ Frontend cache path fixed (package.json)"
echo ""

git push origin security-hardening

echo ""
echo "✅ Pushed successfully!"
echo ""
echo "⏳ Waiting for CI/CD to start (~5 seconds)..."
sleep 5

echo "🔄 Watching CI/CD run (press Ctrl+C to exit)..."
gh run watch --repo zeidalqadri/dbcooper

echo ""
echo "🎉 CI/CD completed!"
echo "🔗 View PR: https://github.com/zeidalqadri/dbcooper/pull/1"
