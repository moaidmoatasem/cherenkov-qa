# CHERENKOV — Diagrams (Mermaid, render on GitHub)

System, sequence, flow, and lifecycle diagrams. Companion to [`docs/vision/01_ARCHITECTURE.md`](../vision/01_ARCHITECTURE.md) and [`docs/process/GITHUB_PM.md`](../process/GITHUB_PM.md).

---

## 1. System context

```mermaid
flowchart TB
  Dev([Developer / QA]); Agent([Autonomous Agent]); CI([CI/CD])
  subgraph CK[CHERENKOV]
    Core[Reasoning Harness + Truth Model]
  end
  subgraph Src[Sources]
    S1[OpenAPI]; S2[Traffic/OTel]; S3[DB schema]; S4[Code/UI]
  end
  subgraph Mod[Models via Substrate Router]
    M1[Local Ollama/vLLM]; M2[Cloud OpenAI/Anthropic]
  end
  subgraph Out[Artifacts]
    O1[Playwright]; O2[Spec patch]; O3[PR comment/report]
  end
  Dev-->CK; Agent-->CK; CI-->CK
  Src-->CK; CK<-->Mod; CK-->Out; Out-->CI
```

## 2. Track A pipeline (sequence) — spec in, tests out

```mermaid
sequenceDiagram
  participant U as User
  participant IN as INGEST
  participant PL as PLAN (deepseek)
  participant GE as GENERATE (qwen)
  participant RV as REVIEW (6 gates)
  participant FS as tests/
  U->>IN: OpenAPI spec
  IN->>IN: parse + depth-1 slice, openapi-fetch stub, mutation menu
  IN->>PL: endpoint slices + menu
  PL->>PL: select mutation_id (never invents), strip <think>
  PL->>GE: chosen scenario
  GE->>GE: write test w/ openapi-fetch (static prompt → prefix cache)
  GE->>RV: candidate test
  RV->>RV: syntax→structure→AST→assertions→tsc --noEmit→Prism dry-run
  alt verdict auto_approve (>0.9)
    RV->>FS: write test
  else dry-run fail
    RV-->>PL: D2 loop back (circuit-break at 2 fails/case)
  else hitl (0.7–0.9)
    RV->>U: human review
  end
```

## 3. Divergence loop (sequence) — THE BET

```mermaid
sequenceDiagram
  participant TM as Truth Model
  participant K as Skeptic
  participant Sub as Substrate Router
  participant W as Witness
  participant T as Target System
  participant Sc as Scribe
  TM->>K: two claims about endpoint X (spec vs traffic)
  K->>Sub: ReasoningRequest{tier} "where do these diverge?"
  Sub-->>K: hypothesis (D1–D5) + predicted evidence
  K->>W: divergence hypothesis
  W->>T: fire minimal real request
  T-->>W: real response
  W->>W: diff real vs claim
  alt reproduced
    W->>Sc: confirmed + evidence
    Sc-->>TM: update + emit artifact
  else not reproduced
    W-->>K: reject (tautology/noise)
  end
```

## 4. Reflector learning loop (sequence) — Epoch 7 (proposed)

```mermaid
sequenceDiagram
  participant W as Witness/Healing
  participant H as Human (Verdict)
  participant R as Reflector
  participant DB as verdicts.db
  participant K as Skeptic
  participant Sc as Scribe
  W->>R: ReproductionResult / FailureClass
  H->>R: accept | reject | refine (+reason)
  R->>DB: persist VerdictRecord / Idiom
  R->>K: reweight hypothesis ranking (rejected stop recurring)
  R->>Sc: idiom updates (what to emit / check)
  Note over R,DB: Exit = behavioral: rejected findings don't return; hit-rate ↑
```

## 5. FE user journey (flowchart) — manual-QA first

```mermaid
flowchart TD
  A[Land on Overview<br/>release readiness] --> B{What now?}
  B -->|See risk| C[Divergences ★<br/>severity-sorted findings]
  B -->|Explore build| D[Explore ★<br/>second pair of eyes]
  B -->|Author test| E[Author by Intent ★<br/>plain English]
  D --> C
  C --> F[Open finding<br/>claim A vs B + evidence]
  F -->|Close with test| G[Pilot executes live<br/>vision-confirmed]
  E --> G
  G --> H[Review Queue<br/>approve / reject + reason]
  H -->|teaches| I[(Reflector memory)]
  H -->|approve| J[Eject standalone Playwright<br/>zero lock-in]
  I -.idioms.-> E
```

## 6. Application lifecycle — issue/ticket state machine

```mermaid
stateDiagram-v2
  [*] --> Ready: acceptance written, labels set (DoR)
  Ready --> InProgress: branch feat/<issue>-slug
  InProgress --> InReview: PR opened (+ raw evidence)
  InReview --> InProgress: changes requested
  InReview --> Done: checks green + approved + squash-merge
  InProgress --> Blocked: dependency / gate
  Blocked --> Ready: unblocked
  Done --> [*]
```

## 7. Git / PR flow

```mermaid
flowchart LR
  M[(main protected)] -->|branch| B[feat/123-slug]
  B --> C[commits: Conventional + #123]
  C --> P[PR: template + evidence + Closes #123]
  P --> CK{CI checks<br/>Docs · Healing · CLI · CodeQL}
  CK -->|fail| C
  CK -->|pass| RV{1+ approval<br/>threads resolved}
  RV -->|changes| C
  RV -->|approve| SQ[squash-merge] --> M
  SQ --> CL[issue auto-closed<br/>milestone burns down]
```

## 8. Release flow

```mermaid
flowchart LR
  MS[Milestone complete] --> CH[Update CHANGELOG.md]
  CH --> TG[git tag vX.Y]
  TG --> Rel[GitHub Release<br/>notes from CHANGELOG]
  Rel --> Pre{validation gate passed?}
  Pre -->|no| PR[mark pre-release]
  Pre -->|yes| GA[mark latest]
```
