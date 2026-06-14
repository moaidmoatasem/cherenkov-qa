import os
import re

ui_src_dir = "cherenkov/web/ui/src/components"
app_file = "cherenkov/web/ui/src/App.tsx"

# We already fixed SetupScreen and App, but let's be thorough if any leftovers

# PipelineScreen
pipeline_path = os.path.join(ui_src_dir, "PipelineScreen.tsx")
with open(pipeline_path, "r") as f:
    content = f.read()
content = content.replace("import { PIPELINE_STREAMING_TESTS } from '../mockData';", "")
content = content.replace(
    "PIPELINE_STREAMING_TESTS[currentTestIndex] || PIPELINE_STREAMING_TESTS[0]",
    "realTestQueue[currentTestIndex] || { endpoint: 'Waiting for stream...', code: '', agent: 'System' }",
)
content = content.replace("PIPELINE_STREAMING_TESTS.length", "realTestQueue.length")
with open(pipeline_path, "w") as f:
    f.write(content)

# OverviewScreen
overview_path = os.path.join(ui_src_dir, "OverviewScreen.tsx")
with open(overview_path, "r") as f:
    content = f.read()
content = content.replace(
    "import { MOCK_OVERVIEW } from '../mockData';",
    "import { fetchOverview } from '../lib/api';",
)
# We need to change the state initialization
content = re.sub(
    r"export default function OverviewScreen[^{]+\{",
    "export default function OverviewScreen({ onNewRun, onNavigate }: OverviewScreenProps) {\n  const [overview, setOverview] = React.useState<any>(null);\n  React.useEffect(() => { fetchOverview().then(setOverview); }, []);\n  if (!overview) return null;\n  const MOCK_OVERVIEW = overview;",
    content,
)
with open(overview_path, "w") as f:
    f.write(content)

# HealingScreen
healing_path = os.path.join(ui_src_dir, "HealingScreen.tsx")
with open(healing_path, "r") as f:
    content = f.read()
content = content.replace(
    "import { INITIAL_FAILURES } from '../mockData';",
    "import { fetchFailures } from '../lib/api';",
)
content = re.sub(
    r"const \[failures, setFailures\] = useState<FailureEvent\[\]>\(INITIAL_FAILURES\);",
    "const [failures, setFailures] = useState<FailureEvent[]>([]);\n  React.useEffect(() => { fetchFailures().then(setFailures); }, []);",
    content,
)
with open(healing_path, "w") as f:
    f.write(content)

# TruthMapScreen
truth_path = os.path.join(ui_src_dir, "TruthMapScreen.tsx")
with open(truth_path, "r") as f:
    content = f.read()
content = content.replace(
    "import { MOCK_TRUTH_MAP } from '../mockData';",
    "import { fetchTruthMap } from '../lib/api';",
)
content = re.sub(
    r"const \[nodes, setNodes\] = useState<TruthNode\[\]>\(MOCK_TRUTH_MAP\);",
    "const [nodes, setNodes] = useState<TruthNode[]>([]);\n  React.useEffect(() => { fetchTruthMap().then(setNodes); }, []);",
    content,
)
with open(truth_path, "w") as f:
    f.write(content)

# SignalsScreen
signals_path = os.path.join(ui_src_dir, "SignalsScreen.tsx")
with open(signals_path, "r") as f:
    content = f.read()
content = content.replace(
    "import { MOCK_SIGNALS } from '../mockData';",
    "import { fetchSignals } from '../lib/api';",
)
content = re.sub(
    r"export default function SignalsScreen[^{]+\{",
    "export default function SignalsScreen() {\n  const [MOCK_SIGNALS, setSignals] = React.useState<any>({ performance: [], visual: [], coverage: {} });\n  React.useEffect(() => { fetchSignals().then(setSignals); }, []);\n",
    content,
)
with open(signals_path, "w") as f:
    f.write(content)

# GovernanceScreen
gov_path = os.path.join(ui_src_dir, "GovernanceScreen.tsx")
with open(gov_path, "r") as f:
    content = f.read()
content = content.replace(
    "import { MOCK_GOVERNANCE } from '../mockData';",
    "import { fetchGovernance } from '../lib/api';",
)
content = re.sub(
    r"export default function GovernanceScreen[^{]+\{",
    "export default function GovernanceScreen() {\n  const [MOCK_GOVERNANCE, setGov] = React.useState<any>({ score: 100, issues: [] });\n  React.useEffect(() => { fetchGovernance().then(setGov); }, []);\n",
    content,
)
with open(gov_path, "w") as f:
    f.write(content)

# MemoryScreen
memory_path = os.path.join(ui_src_dir, "MemoryScreen.tsx")
with open(memory_path, "r") as f:
    content = f.read()
content = content.replace(
    "import { MOCK_IDIOMS, MOCK_PAIRING } from '../mockData';",
    "import { fetchMemory } from '../lib/api';",
)
content = re.sub(
    r"export default function MemoryScreen[^{]+\{",
    "export default function MemoryScreen() {\n  const [mem, setMem] = React.useState<any>({ idioms: [], pairing: [] });\n  React.useEffect(() => { fetchMemory().then(setMem); }, []);\n  const MOCK_IDIOMS = mem.idioms;\n  const MOCK_PAIRING = mem.pairing;\n",
    content,
)
with open(memory_path, "w") as f:
    f.write(content)

# AuthorScreen
author_path = os.path.join(ui_src_dir, "AuthorScreen.tsx")
with open(author_path, "r") as f:
    content = f.read()
content = content.replace(
    "import { MOCK_MENTOR_IDIOMS } from '../mockData';",
    "import { fetchMemory } from '../lib/api';",
)
content = re.sub(
    r"export default function AuthorScreen[^{]+\{",
    "export default function AuthorScreen() {\n  const [MOCK_MENTOR_IDIOMS, setIdioms] = React.useState<any>([]);\n  React.useEffect(() => { fetchMemory().then(d => setIdioms(d.idioms)); }, []);\n",
    content,
)
with open(author_path, "w") as f:
    f.write(content)

# EjectScreen
eject_path = os.path.join(ui_src_dir, "EjectScreen.tsx")
with open(eject_path, "r") as f:
    content = f.read()
content = content.replace("import { MOCK_FILE_TREE } from '../mockData';", "")
content = re.sub(
    r"const \[files, setFiles\] = useState<FileNode\[\]>\(MOCK_FILE_TREE\);",
    "const [files, setFiles] = useState<FileNode[]>([]);",
    content,
)
with open(eject_path, "w") as f:
    f.write(content)

print("Patching complete.")
