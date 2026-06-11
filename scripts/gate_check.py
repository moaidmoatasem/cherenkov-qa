import os
import re
import sys

def check_gate():
    ledger_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'process', 'VALIDATION_EVIDENCE_LEDGER.md')
    if not os.path.exists(ledger_path):
        print("ERROR: Evidence ledger not found.")
        sys.exit(1)
        
    with open(ledger_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Count rows that have "Yes" in the Vote column and are not _pending_
    yes_count = 0
    # Extract the table rows
    for line in content.split('\n'):
        if line.startswith('|') and 'Yes' in line and '_pending_' not in line:
            yes_count += 1
            
    # Check for mobile and chat in evidence directory
    evidence_dir = os.path.join(os.path.dirname(__file__), '..', 'docs', 'process', 'evidence')
    has_mobile = False
    has_chat = False
    
    if os.path.exists(evidence_dir):
        for fname in os.listdir(evidence_dir):
            if fname.endswith('.md'):
                with open(os.path.join(evidence_dir, fname), 'r', encoding='utf-8') as ef:
                    ef_content = ef.read().lower()
                    if 'mobile' in ef_content:
                        has_mobile = True
                    if 'chat' in ef_content:
                        has_chat = True
                        
    print(f"Current 'Yes' verdicts: {yes_count}")
    print(f"Mobile evidence: {'Found' if has_mobile else 'Missing'}")
    print(f"Chat evidence: {'Found' if has_chat else 'Missing'}")
    
    if yes_count >= 5 and has_mobile and has_chat:
        print("GATE PASSED: All conditions met.")
        sys.exit(0)
    else:
        print("GATE OPEN: Conditions not met. Need >= 5 'Yes' verdicts, including 1 mobile and 1 chat.")
        sys.exit(1)

if __name__ == '__main__':
    check_gate()
