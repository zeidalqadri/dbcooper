#!/bin/bash
# Push full CI/CD pipeline to public repository

set -e

echo "🚀 Pushing full CI/CD pipeline to public repository..."
echo ""
echo "Repository: https://github.com/zeidalqadri/dbcooper (PUBLIC)"
echo "Branch: security-hardening"
echo "Commits to push: 2"
echo ""

git push origin security-hardening

echo ""
echo "✅ Pushed successfully!"
echo ""
echo "🔄 CI/CD Pipeline will now run with:"
echo "   - Multiple Python versions (3.10, 3.11, 3.12)"
echo "   - PostgreSQL 16 integration tests"
echo "   - Frontend build and tests"
echo "   - Full coverage reporting"
echo "   - Security scans"
echo ""
echo "⏳ Watching CI/CD run (press Ctrl+C to exit)..."
sleep 3

gh run watch --repo zeidalqadri/dbcooper

echo ""
echo "🎉 CI/CD completed!"
echo ""
echo "🔗 View PR: https://github.com/zeidalqadri/dbcooper/pull/1"
echo "📊 Check test results and coverage in the Actions tab"
