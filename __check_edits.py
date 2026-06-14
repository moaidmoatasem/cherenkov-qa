files = [
    ('/home/moaid/cherenkov-qa/cherenkov.py', 'accessibility' in open('/home/moaid/cherenkov-qa/cherenkov.py').read()),
    ('/home/moaid/cherenkov-qa/cherenkov/daemon/trigger_loop.py', 'elif self.source_type == "grpc"' in open('/home/moaid/cherenkov-qa/cherenkov/daemon/trigger_loop.py').read()),
    ('/home/moaid/cherenkov-qa/cherenkov/daemon/trigger_loop.py', 'AccessibilityScenarioPlanner' in open('/home/moaid/cherenkov-qa/cherenkov/daemon/trigger_loop.py').read()),
    ('/home/moaid/cherenkov-qa/cherenkov/mcp/handlers.py', 'type="string", description="Validation item ID."' in open('/home/moaid/cherenkov-qa/cherenkov/mcp/handlers.py').read()),
]
for path, result in files:
    print(f'{path}: {result}')
