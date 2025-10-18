#!/bin/bash
# Push CI/CD fixes to now-public repository

set -e

echo "🌍 Repository is now PUBLIC!"
echo "   URL: https://github.com/zeidalqadri/dbcooper"
echo "   Benefits: ✅ Unlimited GitHub Actions minutes"
echo ""
echo "🚀 Pushing CI/CD fixes..."
git push origin security-hardening

echo ""
echo "✅ Fixes pushed successfully!"
echo ""
echo "🔗 View PR: https://github.com/zeidalqadri/dbcooper/pull/1"
echo ""
echo "⏳ Waiting for CI/CD checks to run..."
sleep 5
gh run watch --repo zeidalqadri/dbcooper

echo ""
echo "🎉 All done! Repository is public with working CI/CD."
