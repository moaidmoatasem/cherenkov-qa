#!/usr/bin/env bash
# CHERENKOV Stacked PR Push & Merge Automation
# Automated stack management with GitHub Stack CLI integration

# Configuration
STACK_ID="${1:-auth-stack}"
STRATEGY="${2:-functional}"
EPIIC_ID="${3:-ENG-123}"

# Load setup script
. scripts/setup_git_stack_config.sh

# Initialize stack configuration
cat > stack_config.json << EOF
{
  "stack_id": "${STACK_ID}",
  "strategy": "${STRATEGY}",
  "epic_issue_id": "${EPIIC_ID}",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "active",
  "layers": [
    {
      "layer_index": 0,
      "layer_name": "01-contracts",
      "branch_name": "feat/01-contracts",
      "base_branch": "main",
      "status": "created"
    }
  ]
}
EOF

# Initialize GitHub Stack if available
if command -v gh &> /dev/null; then
    echo "🚀 Initializing GitHub Stack: ${STACK_ID}"
    gh stack init "${STACK_ID}" --description "Stacked PR for ${EPIIC_ID}"
    echo "✅ GitHub Stack created"
else
    echo "⚠️  GitHub Stack CLI not available, using standard Git workflow"
fi

# Create first layer
echo "📝 Creating first layer: 01-contracts"
git checkout -b "feat/01-contracts" main 2>/dev/null || {
    echo "⚠️  Could not create branch feat/01-contracts"
}

# Create layer metadata
cat > "${STACK_ID}_layer_0.meta.json" << EOF
{
  "stack_id": "${STACK_ID}",
  "layer_index": 0,
  "layer_name": "01-contracts",
  "branch_name": "feat/01-contracts",
  "base_branch": "main",
  "instruction": "Create JWT authentication contracts and database schemas",
  "status": "pending",
  "target_paths": ["src/core/contracts.py", "src/ports/auth_port.py"],
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "✅ Initial stack created with layer 0"
echo ""
echo "🎯 Stack Operations Available:"
echo "  1. scripts/stack_push_merge_alignment.sh init <stack_id> <strategy> <epic_id>"
echo "  2. scripts/stack_push_merge_alignment.sh create-layer <stack_id> <layer_index> <layer_name> <instruction> <base_branch>"
echo "  3. scripts/stack_push_merge_alignment.sh push-layer <stack_id> <layer_index> <commit_message>"
echo "  4. scripts/stack_push_merge_alignment.sh sync"
echo "  5. scripts/stack_push_merge_alignment.sh merge"
echo "  6. scripts/stack_push_merge_alignment.sh status <stack_id>"
echo ""
echo "🚀 Next step: scripts/stack_push_merge_alignment.sh create-layer ${STACK_ID} 1 02-jwt-service \"Implement JWT authentication using Layer 1 contracts\" feat/01-contracts"
