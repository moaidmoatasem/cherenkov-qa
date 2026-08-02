#!/usr/bin/env bash
# Comprehensive Stack Push & Merge Alignment System
# Integrates GitHub Stack CLI with CHERENKOV's multi-layer PR workflow

# Source the setup script
. scripts/setup_git_stack_config.sh

# Stack Configuration
STACK_CONFIG_FILE="stack_config.json"

# Load stack configuration
load_stack_config() {
    if [ -f "$STACK_CONFIG_FILE" ]; then
        echo "Loading stack configuration..."
        export $(jq -r 'to_entries | map("export \(.key)='\\''\(.value)'\\''") | join " \"')' "$STACK_CONFIG_FILE" 2>/dev/null
    fi
}

# Initialize stack with GitHub Stack CLI
init_github_stack() {
    local stack_id="$1"
    local strategy="$2"
    local epic_issue="$3"
    
    echo "🚀 Initializing GitHub Stack for ${stack_id}"
    echo "   Strategy: ${strategy}"
    echo "   Epic Issue: ${epic_issue}"
    
    # Initialize GitHub Stack repository
    if command -v gh &> /dev/null; then
        gh stack init "${stack_id}"
        echo "✅ GitHub Stack initialized: ${stack_id}"
    else
        echo "⚠️  GitHub Stack CLI not available. Using standard Git workflow."
    fi
    
    # Create initial layer (layer 0) if not exists
    if [ ! -f "${stack_id}_layer_0.meta.json" ]; then
        echo "📝 Creating initial layer (layer 0)"
        create_stack_layer "${stack_id}" "0" "01-contracts" "Initial contracts and base schemas" "main"
    fi
}

# Create a new stack layer with GitHub Stack integration
create_stack_layer() {
    local stack_id="$1"
    local layer_index="$2"
    local layer_name="$3"
    local instruction="$4"
    local base_branch="$5"
    
    echo "🏗️  Creating stack layer: ${layer_name} (index: ${layer_index})"
    
    # Check if layer already exists
    if [ -f "${stack_id}_layer_${layer_index}.meta.json" ]; then
        echo "⚠️  Layer ${layer_index} already exists. Skipping."
        return
    fi
    
    # Create meta data file
    cat > "${stack_id}_layer_${layer_index}.meta.json" << EOF
{
  "stack_id": "${stack_id}",
  "layer_index": ${layer_index},
  "layer_name": "${layer_name}",
  "branch_name": "feat/${layer_name}",
  "base_branch": "${base_branch}",
  "instruction": "${instruction}",
  "status": "pending",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "github_pr_number": null,
  "sdx_context": null
}
EOF
    
    # Create actual Git branch if GitHub Stack is not available
    if ! command -v gh &> /dev/null; then
        git checkout -b "feat/${layer_name}" "${base_branch}" 2>/dev/null || {
            echo "⚠️  Could not create branch feat/${layer_name}. Continuing with meta data only."
        }
    fi
    
    echo "✅ Stack layer ${layer_name} created (index: ${layer_index})"
}

# Push layer changes with GitHub Stack integration
push_stack_layer() {
    local stack_id="$1"
    local layer_index="$2"
    local commit_message="$3"
    local commit_files="$4"
    
    echo "📤 Pushing stack layer ${layer_index}...
"
    echo "   Stack ID: ${stack_id}"
    echo "   Layer Index: ${layer_index}"
    echo "   Commit Message: ${commit_message}"
    
    # Check if stack exists
    if [ ! -f "${stack_id}_layer_${layer_index}.meta.json" ]; then
        echo "❌ Layer ${layer_index} does not exist in stack ${stack_id}"
        return 1
    fi
    
    # Stage files if provided
    if [ -n "$commit_files" ]; then
        for file in $commit_files; do
            if [ -f "$file" ]; then
                git add "$file"
                echo "   Added: $file"
            else
                echo "   ⚠️  File not found: $file"
            fi
        done
    fi
    
    # Commit with stack-aware message
    git commit -m "stack: ${stack_id} - layer ${layer_index} - ${commit_message}" \
                -m "Layer: ${layer_index}-${layer_name}" \
                -m "Stack: ${stack_id}" \
                -m "Status: progressing"
    
    # Push to remote
    if command -v gh &> /dev/null; then
        git push origin "feat/${layer_name}" || {
            echo "❌ Failed to push layer ${layer_index} to remote"
            return 1
        }
    else
        git push origin "feat/${layer_name}" || {
            echo "❌ Failed to push layer ${layer_index} to remote"
            return 1
        }
    fi
    
    # Update layer status in meta file
    if [ -f "${stack_id}_layer_${layer_index}.meta.json" ]; then
        jq --arg status "committed" '.status = $status' "${stack_id}_layer_${layer_index}.meta.json" > "${stack_id}_layer_${layer_index}.meta.json.tmp" && \
        mv "${stack_id}_layer_${layer_index}.meta.json.tmp" "${stack_id}_layer_${layer_index}.meta.json"
    fi
    
    echo "✅ Stack layer ${layer_index} pushed successfully"
    echo "   Branch: feat/${layer_name}"
    echo "   Commit: $(git rev-parse HEAD | cut -c1-8)"
}

# Sync stack dependencies after a layer push
sync_stack_dependencies() {
    echo "🔄 Syncing stack dependencies..."
    
    if command -v gh &> /dev/null; then
        echo "   Using GitHub Stack CLI for dependency management"
        gh stack sync
    else
        echo "   ⚠️  GitHub Stack CLI not available. Using manual sync.\n"
        echo "   Running cascading rebase...
"
        git rebase --continue || {
            echo "⚠️  Rebase conflicts may need manual resolution"
        }
    fi
    
    echo "✅ Stack dependencies sync completed"
}

# Merge stack layers using GitHub Merge Queue
merge_stack_layers() {
    echo "🔄 Merging stack layers..."
    
    if [ "$MERGE_QUEUE_ENABLED" = "true" ]; then
        echo "   Using GitHub Merge Queue for layer ordering"
        echo "   Note: Merge Queue requires manual intervention in repository settings"
        echo "   - Enable merge queue in repository Settings > Branches"
        echo "   - Configure queue strategy (squash or rebase)"
        echo "   - Set up branch protection for main"
    else
        echo "   ⚠️  Merge Queue not enabled. Manual merge order required."
        echo "   Consider using gh stack merge command or standard git workflow"
    fi
    
    echo "✅ Stack merge instructions provided"
}

# Validate stack integrity
validate_stack_integrity() {
    local stack_id="$1"
    
    echo "🔍 Validating stack integrity for ${stack_id}..."
    
    # Check if stack metadata exists
    if [ ! -f "${stack_id}.stack.json" ]; then
        echo "❌ Stack metadata not found: ${stack_id}.stack.json"
        return 1
    fi
    
    # Check each layer
    local layers_valid=true
    for layer_file in "${stack_id}_layer_*.meta.json"; do
        if [ -f "$layer_file" ]; then
            echo "   ✓ Layer file: $(basename "$layer_file")"
        else
            echo "   ❌ Missing layer file"
            layers_valid=false
        fi
    done
    
    if [ "$layers_valid" = true ]; then
        echo "✅ Stack integrity validation passed"
    else
        echo "❌ Stack integrity validation failed"
        return 1
    fi
}

# Print stack status
print_stack_status() {
    local stack_id="$1"
    
    echo "📊 Stack Status: ${stack_id}"
    echo "================================"
    
    if [ -f "${stack_id}.stack.json" ]; then
        local epic_issue=$(jq -r '.epic_issue_id' "${stack_id}.stack.json" 2>/dev/null)
        local strategy=$(jq -r '.strategy' "${stack_id}.stack.json" 2>/dev/null)
        local status=$(jq -r '.status' "${stack_id}.stack.json" 2>/dev/null)
        
        echo "Epic Issue: ${epic_issue}"
        echo "Strategy: ${strategy}"
        echo "Status: ${status}"
        
        echo ""
        echo "Layer Files:"
        for layer_file in "${stack_id}_layer_*.meta.json"; do
            if [ -f "$layer_file" ]; then
                local layer_index=$(jq -r '.layer_index' "$layer_file" 2>/dev/null)
                local layer_name=$(jq -r '.layer_name' "$layer_file" 2>/dev/null)
                local branch_name=$(jq -r '.branch_name' "$layer_file" 2>/dev/null)
                local status=$(jq -r '.status' "$layer_file" 2>/dev/null)
                
                echo "  Layer ${layer_index}: ${layer_name} (${branch_name}) - ${status}"
            fi
        done
    else
        echo "❌ Stack metadata not found"
    fi
}

# Main script execution
main() {
    # Load configuration
    load_stack_config
    
    echo "🚀 Stacked PR Push & Merge Alignment Tool"
    echo "=========================================="
    echo ""
    
    case "$1" in
        "init")
            if [ -z "$2" ] || [ -z "$3" ] || [ -z "$4" ]; then
                echo "Usage: $0 init <stack_id> <strategy> <epic_issue>"
                echo "Example: $0 init auth-stack functional ENG-123"
                exit 1
            fi
            init_github_stack "$2" "$3" "$4"
            ;;
        
        "create-layer")
            if [ -z "$2" ] || [ -z "$3" ] || [ -z "$4" ] || [ -z "$5" ] || [ -z "$6" ]; then
                echo "Usage: $0 create-layer <stack_id> <layer_index> <layer_name> <instruction> <base_branch>"
                exit 1
            fi
            create_stack_layer "$2" "$3" "$4" "$5" "$6"
            ;;
        
        "push-layer")
            if [ -z "$2" ] || [ -z "$3" ] || [ -z "$4" ]; then
                echo "Usage: $0 push-layer <stack_id> <layer_index> <commit_message> [files...]"
                exit 1
            fi
            push_stack_layer "$2" "$3" "$4" "$5"
            sync_stack_dependencies
            ;;
        
        "sync")
            sync_stack_dependencies
            ;;
        
        "merge")
            merge_stack_layers
            ;;
        
        "validate")
            if [ -z "$2" ]; then
                echo "Usage: $0 validate <stack_id>"
                exit 1
            fi
            validate_stack_integrity "$2"
            ;;
        
        "status")
            if [ -z "$2" ]; then
                echo "Usage: $0 status <stack_id>"
                exit 1
            fi
            print_stack_status "$2"
            ;;
        
        *)
            echo "Usage: $0 <command> [options]"
            echo ""
            echo "Commands:"
            echo "  init <stack_id> <strategy> <epic_issue>      Initialize a new stack"
            echo "  create-layer <stack_id> <layer_index> <layer_name> <instruction> <base_branch>"
            echo "                                                  Create a new layer in the stack"
            echo "  push-layer <stack_id> <layer_index> <commit_message> [files...]"
            echo "                                                Push layer changes to remote"
            echo "  sync                                            Sync stack dependencies"
            echo "  merge                                            Merge stack layers"
            echo "  validate <stack_id>                             Validate stack integrity"
            echo "  status <stack_id>                                Print stack status"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
