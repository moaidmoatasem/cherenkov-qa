---
name: cherenkov-stack-orchestrator
---

# Skill: CHERENKOV Stack Orchestrator
**Purpose:** Automatically create and manage stacked pull requests for complex feature development in CHERENKOV.

**Pattern:** Plan-First Stack Generation (Strategy + Layer Breakdown)
**Invariant:** Each PR layer must have explicit dependency ordering and stack-aware CI gating

## When To Load This Skill

Load this skill when:
- You're an autonomous agent tasked with a complex feature (e.g., "add JWT authentication", "refactor contracts")
- The feature naturally decomposes into multiple architectural layers (contracts → adapters → use_cases → api → tests)
- You need to create dependent changes that build logically on each other
- The feature is too large for a single review but can be broken into logical, testable units

## Prerequisites

Before loading this skill, you must:
1. **Analyze the feature requirement** and identify logical architectural boundaries
2. **Determine stack strategy** (functional, refactor_first, risk_isolated) based on the feature
3. **Identify layer decomposition** - what changes are needed for each layer
4. **Verify no CI/CD conflicts** with existing workflow configurations

## Workflow

### Step 1: Plan Stack Strategy Before Implementation

```bash
# Analyze the feature
python3 -c "
import json
feature = 'add JWT authentication'
# Determine strategy based on feature characteristics
if 'auth' in feature.lower():
    print('Strategy: risk_isolated (authentication is high-risk)')
    print('Layers: 01-risk (auth schemas) -> 02-normal (JWT service) -> 03-normal (api endpoints)')
else:
    print('Strategy: functional (standard decomposition)')
    print('Layers: 01-contracts -> 02-adapters -> 03-use-cases -> 04-cli-api -> 05-tests')
"
```

**Critical:** DO NOT execute any Git commands or generate code until you have this plan approved.

### Step 2: Generate Stack Plan Text

Create a comprehensive stack plan with the following structure:

```
STACK PLAN for: [Feature Name]

=== STACK METADATA ===
Stack ID: stack_[uuid]
Epic Issue: [issue-reference]
Strategy: [functional|refactor_first|risk_isolated]
Layer Count: [N]
Total Budget: [X] tokens

=== LAYER BREAKDOWN ===
Layer 1: [01-contracts] - [Descriptive title]
  Purpose: [Explain why this layer is needed first]
  Files: [src/core/contracts.py, src/ports/auth_port.py, prisma/auth_schema.prisma]
  Budget: [25000] tokens
  SDD Context: base (no inheritance)
  Dependencies: None

Layer 2: [02-adapters] - [Descriptive title]
  Purpose: [Explain dependency on Layer 1]
  Files: [src/adapters/auth_adapter.py, tests/unit/adapters/auth_test.py]
  Budget: [25000] tokens
  SDD Context: inherit_from Layer 1
  Dependencies: Layer 1 contracts

Layer N: [NN-title] - [Descriptive title]
  Purpose: [Explain dependency on Layer N-1]
  Files: [src/api/jwt_routes.py, src/services/jwt_service.py, tests/e2e/jwt_test.py]
  Budget: [25000] tokens
  SDD Context: inherit_from Layer N-1
  Dependencies: Layer N-1

=== EXECUTION PLAN ===
1. [ ] Create stack orchestration record in SDD
2. [ ] For each layer in order:
   a. Create git branch (layer-specific prefix)
   b. Initialize SDD session with inheritance from previous layer
   c. Execute sub-agent task for this layer
   d. Submit PR (draft) with explicit base branch = previous layer
3. [ ] Sync all layers via gh stack submit
4. [ ] Wait for human review and approval
5. [ ] Execute cascading rebase validation
```

### Step 3: Validate Stack Plan Before Implementation

Before you or any agent proceeds, validate:

```bash
# Validate stack integrity using the stacked_conductor
python3 << 'EOF'
from cherenkov.agents.conductor.adapters.stacked_conductor import create_and_execute_stack
from cherenkov.agents.conductor.domain.models import StackStrategy, PRSubTask

# Define layers based on your plan
layers = [
    PRSubTask(
        layer_index=0,
        layer_name="01-auth-schemas",
        branch_name="01-auth-schemas",
        base_branch="main",
        instruction="Create JWT authentication schemas and database migrations",
        target_paths=["src/core/contracts.py", "src/ports/auth_port.py", "prisma/auth_schema.prisma"],
    ),
    PRSubTask(
        layer_index=1,
        layer_name="02-jwt-service",
        branch_name="02-jwt-service",
        base_branch="01-auth-schemas",
        instruction="Implement JWT service layer using contracts from Layer 1",
        target_paths=["src/services/jwt_service.py", "src/adapters/jwt_adapter.py"],
    ),
    # ... more layers
]

# Validate stack coherence
print("Stack validation:")
for i, layer in enumerate(layers):
    if layer.base_branch != (f"{i:02d}-functional" if i > 0 else "main"):
        print(f"  ❌ Layer {layer.layer_index}: Base mismatch")
    else:
        print(f"  ✅ Layer {layer.layer_index}: {layer.layer_name} OK")

EOF
```

### Step 4: Execute Stack Plan (Post-Approval)

Once the stack plan is approved, execute it using the stacked orchestrator:

```bash
# Initialize SDD stack context
python3 scripts/stack_management.py before \
  --epic "ENG-123" \
  --strategy "risk_isolated" \
  --budget 50000

# Add each layer sequentially
python3 scripts/stack_management.py add-layer \
  --stack-id "$STACK_ID" \
  --layer-index 0 \
  --layer-name "01-auth-schemas" \
  --branch-name "01-auth-schemas" \
  --base-branch "main" \
  --instruction "Create JWT authentication schemas and database migrations" \
  --target-paths "src/core/contracts.py src/ports/auth_port.py prisma/auth_schema.prisma"

# After executing each layer, link the PR (adjust PR number as needed)
python3 scripts/stack_management.py link-pr \
  --stack-id "$STACK_ID" \
  --layer-index 0 \
  --pr-number 123

# When all layers are executed, close the stack
python3 scripts/stack_management.py after \
  --stack-id "$STACK_ID" \
  --summary "JWT authentication stack implemented with Layer 1 contracts, Layer 2 service implementation, and Layer 3 API integration"
```

### Step 5: Stack Submission and Sync

```bash
# Submit the stack for GitHub integration
# This creates all branches, PRs, and syncs dependencies automatically
gh stack submit --auto

# Or use ezstack for worktree-based workflow
ezs agent stack submit --auto
```

### Step 6: Review and Iterate

```bash
# Review the status of the stack
python3 scripts/stack_management.py status --stack-id "$STACK_ID"

# If you need to adjust the stack, use gh-stack or ezstack modify commands
gh stack modify --insert-layer-before 1 --new-layer "refactor/authentication_logic"

# Review specific layer using SDD context
agent_sync experience query "stack_${STACK_ID}"
```

## Integration with Other Skills

### With SDD Skill

1. **Before implementing each layer**, run SDD to load context:
```bash
agent_sync before --task "layer_01_auth_schemas"
```

2. **After implementing each layer**, run SDD to capture decisions:
```bash
agent_sync after --summary "Created authentication contracts in Layer 1"
```

### With Qwen Code Subagent Skills

When using Qwen Code for individual layers, each subagent should be instructed to:

1. **Acknowledge stack context** in their system prompt
2. **Explicitly state stack layer dependencies** in their instructions
3. **Report layer boundaries violations** immediately

Example Qwen Code instruction:
> "You are working on CHERENKOV Stack Layer 2 (02-jwt-service). This layer depends on Layer 1 (01-auth-schemas) contracts. DO NOT modify files from Layer 1. Your work must be contained within src/services/ and src/adapters/ directories only. Report any violations to the user immediately."

### With GitHub Actions Workflows

Each layer's PR triggers the stack-aware CI workflow:

```yaml
events:
  pull_request:
    types: [opened, synchronize, reopened]
    paths:
      - 'src/adapters/**'
      - 'src/services/**'
      - 'src/api/**'
      - '**/*auth*.py'

jobs:
  stack-layer-validation:
    runs-on: ubuntu-latest
    if: contains(github.event.pull_request.labels.*.name, 'stack-layer')
    steps:
      - name: Validate layer boundaries
        run: |
          # Use the layer-guard workflow to validate this specific layer
          gh workflow run layer-guard.yml \
            --field pr_number=${{ github.event.pull_request.number }}
```

## Error Recovery and Stack Repair

### Stack Corrupted

If a stack becomes corrupted (e.g., Layer 1 failed, Layer 2 partially implemented):

```bash
# Delete corrupted stack branches
gh stack delete --stack-id "$STACK_ID"

# Start fresh with adjusted plan
python3 scripts/stack_management.py before --epic "ENG-123" --strategy "functional"
```

### Layer Conflicts

If Layer N conflicts with Layer N-1:

1. **Identify the conflict** using git diff
2. **Determine if it's architectural** (boundary violation) or implementation (merge conflict)
3. **For architectural violations**, delete the conflicting code from Layer N and move it to the appropriate layer
4. **For implementation conflicts**, use standard Git conflict resolution and sync with the stack

### Stack Stuck

If a stack stops progressing:

```bash
# Check stack status
python3 scripts/stack_management.py status --stack-id "$STACK_ID"

# If a layer is stuck, reset it and re-execute
# (Use with caution - only for clean, non-production changes)
```

## Best Practices

### 1. Plan Before Implementing

**Never execute Git commands or generate code until you have a complete stack plan**. A good stack plan takes 15-30 minutes but saves hours of debugging.

### 2. Use Stack Naming Conventions

```bash
# Functional stack naming
feat/01-contracts/feature-name
feat/02-adapters/feature-name
feat/03-use-cases/feature-name

# Refactor-first stack naming
refactor/01-refactor/feature-name
feat/02-feature/feature-name

# Risk-isolated stack naming
risk/01-auth/feature-name
normal/02-jwt-service/feature-name
```

### 3. Document Layer Responsibilities

Each layer should have clear responsibility boundaries:

```python
# Layer 1: Contracts - Define interfaces, types, database schemas
# Layer 2: Adapters - Implement interfaces, adapt external systems
# Layer 3: Use Cases - Orchestrate business logic
# Layer 4: API - Expose use cases as REST/CLI interfaces
# Layer 5: Tests - Validate everything end-to-end
```

### 4. Test Each Layer Independently

Each layer should be independently testable:

```bash
# Test Layer 1 contracts
python -m pytest tests/unit/contracts/

# Test Layer 2 adapters
python -m pytest tests/unit/adapters/

# Test Layer 3 use cases
python -m pytest tests/unit/use_cases/

# Test Layer 4 API
python -m pytest tests/unit/api/

# Test Layer 5 integration
python -m pytest tests/e2e/
```

### 5. Validate with Automated Tools

Run stack validation before and after execution:

```bash
# Validate stack integrity
python3 << 'EOF'
from cherenkov.agents.conductor.adapters.stacked_conductor import create_and_execute_stack
from cherenkov.agents.conductor.domain.models import StackStrategy, PRSubTask

layers = [
    # ... define your layers ...
]

result = create_and_execute_stack(
    epic_issue_id="ENG-123",
    title="Add JWT Authentication",
    strategy=StackStrategy.RISK_ISOLATED,
    layers=layers,
)

print(f"Stack execution completed: {result.status}")
print(f"Total tokens used: {result.total_tokens_used}")
EOF
```

## Troubleshooting

### Common Issues

| Symptom | Cause | Solution |
|---------|-------|----------|
| Layer 2 modifies Layer 1 contracts | Poor boundary definition | Move contract changes to Layer 1 |
| Stack CI fails on unrelated files | Incorrect CI workflow triggers | Use path filters for stack workflows |
| Layer dependencies out of order | Manual intervention | Use stack orchestration tools |
| Infinite rebase loops | Git configuration issues | Reset git config and retry |

### Stack Orchestration Commands

```bash
# View stack status
gh stack status

# Show stack plan
python3 scripts/stack_management.py status --stack-id <id>

# Modify stack (add, remove, reorder layers)
gh stack modify

# Sync stack after changes
gh stack sync

# Submit stack for review
gh stack submit

# Delete stack (careful!)
gh stack delete
```

## References

- [Cherenkov Stacked PR Architecture](https://github.com/moaidmoatasem/cherenkov-qa/blob/main/docs/architecture/STACKED_PR.md)
- [GitHub Stack CLI Documentation](https://cli.github.com/manual/gh_stack)
- [SDD Protocol](https://github.com/moaidmoatasem/cherenkov-qa/blob/main/.qwen/memory/sdd-protocol.md)
- [Multi-Agent Conductor (CC-2)](https://github.com/moaidmoatasem/cherenkov-qa/blob/main/cherenkov/agents/conductor/adapters/mcp_conductor.py)

---
*Skill developed for CHERENKOV AI-native software engineering workflow*
