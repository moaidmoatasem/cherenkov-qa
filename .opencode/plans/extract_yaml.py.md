#!/usr/bin/env python3
"""Extract YAML from a markdown code block and write to a target file."""
import sys, re

if len(sys.argv) < 3:
    print("Usage: extract_yaml.py <source.md> <target>")
    sys.exit(1)

src = sys.argv[1]
tgt = sys.argv[2]

with open(src) as f:
    content = f.read()

# Match content between triple-backtick yaml markers
pattern = re.compile(r'```yaml\n(.+?)```', re.DOTALL)
match = pattern.search(content)
if not match:
    print(f"No yaml code block found in {src}")
    sys.exit(1)

yaml_content = match.group(1)
with open(tgt, 'w') as f:
    f.write(yaml_content)

print(f"Extracted {len(yaml_content)} bytes to {tgt}")
