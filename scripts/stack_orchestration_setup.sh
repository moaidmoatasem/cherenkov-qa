#!/usr/bin/env bash
# Enhanced stack orchestration setup for CHERENKOV with push/merge alignment

# Source the Git configuration
. scripts/setup_git_stack_config.sh

# Initialize Git credentials for stack operations
git config user.email "cherenkov-agent@moatasem.com"
git config user.name "CHERENKOV AI Agent"

# Create a comprehensive configuration file for stack operations
cat > stack_config.json << EOF
{
  "stack_strategy": "functional",
  "layer_naming": "01-contracts,02-adapters,03-use-cases,04-cli-api,05-tests",
  "github_token": "${GITHUB_TOKEN}",
  "repository": "$(git config remote.origin.url)",
  "default_budget_per_layer": 25000,
  "max_concurrent_layers": 3,
  "auto_submit": false,
  "branch_protection": true,
  "merge_queue_enabled": true,
  "layer_guard_enabled": true,
  "stack_validation_enabled": true,
  "sdx_inheritance_enabled": true,
  "ai_review_integration": "github-actions"
}
EOF

echo "✅ Enhanced stack orchestration initialized"
echo "Configuration saved to stack_config.json"
echo ""
echo "🔧 Stack Configuration Summary:"
echo "  - Stack Strategy: functional"
echo "  - Layer Naming: 01-contracts, 02-adapters, 03-use-cases, 04-cli-api, 05-tests"
echo "  - Merge Queue: Enabled"
echo "  - Layer Guard: Enabled"
echo "  - SDX Inheritance: Enabled"
echo "  - AI Review Integration: GitHub Actions"
echo ""
echo "🚀 Next Steps:"
echo "1. Configure GitHub token for API access: export GITHUB_TOKEN=ghp_..."
echo "2. Set up GitHub Merge Queue in repository settings"
echo "3. Configure branch protection for stacked PR workflow:"
echo "   - Protect 'main' branch with required status checks"
echo "   - Enable merge queue with 'squash' method"
echo "   - Configure protection rules for stack branches"
echo "4. Install required GitHub Apps (if needed):"
echo "   - GitHub CLI (gh)"
echo "   - GitHub Stack extension (gh-stack)"
echo "5. Run stack orchestration:"
echo "   python3 scripts/stack_management.py before --epic ENG-123 --strategy functional"
