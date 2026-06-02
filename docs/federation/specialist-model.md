# Divergence-Specialist Fine-Tuning: Signal Hypothesis & Training Design

## 1. Signal Hypothesis

Claim: The divergence-report structure in CHERENKOV exhibits sufficient signal to fine-tune a 3-8B open-weights model to predict divergences from paired TruthFragment inputs better than a generalist baseline.

### Supporting Evidence

**Structured input domain** (TruthFragment):
- Explicit graph of claims: (method, path, schema type, invariant) tuples normalized across endpoints
- Edge types (SOURCE, INFERRED, AUTHORITATIVE) provide provenance signals
- Node properties consistently keyed: endpoint identifiers are canonicalized
- No free text; claims are schema-bound (GraphNode, Claim) -- consistent signal across corpus

**Structured output domain** (Divergence):
- Discrete class space: D1 (spec/code), D2 (code/prod), D3 (ui/spec), D4 (db/code), D5 (spec/prod)
- Binary signal per class: divergence present (yes/no), severity (HIGH/MEDIUM/LOW/CRITICAL)
- Evidential structure: claim_a vs claim_b pair, repro steps, observable HTTP signals
- No regression task; this is multi-label classification with light ranking

**Fine-tuning advantage over generalist:**
- Generalists struggle with structured input (conflate endpoint paths)
- Generalists hallucinate divergences (confuse schema versioning with D1)
- Generalists are slow: 200-500 tokens per prediction vs specialist 64-token budget

**Verdict:** YES, fine-tune. Invest in a specialist.

## 2. Corpus Size Estimate

Minimum: 1000 examples (10^3); Optimal: 10,000 examples (10^4)

### Justification

**Small-model fine-tuning literature:**
- QLoRA + LoRA on 3-8B models typically requires 500-2000 examples for niche classification
- If task aligns with base model (code understanding), 500-1000 suffice
- If task is niche/adversarial (divergence hypothesis), expect 2000-5000 to converge

**Signal-to-noise trade-off:**
- Each report is a hypothesis, not ground truth
- Assume 60-70% precision in Skeptic output
- To get 1000 true positives, collect 1500-1700 reports

**Corpus construction strategy:**
- Phase 1: Deploy opt-in corpus across teams for 4 weeks (target 2000-3000 submissions)
- Phase 2: Manual review/label 300 reports as correct/incorrect
- Phase 3: Train on confident subset (70% precision); test on held-out 10%

## 3. Training Data Shape

### Input: Paired TruthFragments

`json
{
  "input": {
    "fragment_a": {
      "service_id": "api-prod",
      "nodes": [
        {"id": "ep1", "type": "ENDPOINT", "properties": {"method": "GET", "path": "/users/{id}"}}
      ]
    },
    "fragment_b": {
      "service_id": "api-staging",
      "nodes": [
        {"id": "ep1", "type": "ENDPOINT", "properties": {"method": "GET", "path": "/users/{id}"}}
      ]
    }
  },
  "output": [
    {
      "divergence_class": "D1_SPEC_CODE",
      "severity": "HIGH",
      "claim_a": "response.id is uuid",
      "claim_b": "response.id is string",
      "evidence": "Type mismatch on /users/{id}"
    }
  ]
}
`

## 4. Base Model Candidates (3-8B Parameters)

1. **Qwen2.5-Coder-7B** (Alibaba): Code-trained; reasoning; in CHERENKOV stack. Recommendation: START HERE

2. **Mistral-7B** (Mistral AI): Well-trained on code; strong reasoning. Cost: 28GB VRAM

3. **LLaMA 3.2-8B-Instruct** (Meta): Strong instruction tuning; broad knowledge. Cost: 32GB VRAM

## 5. Evaluation Harness Sketch

`python
def score_divergence_list(predicted, ground_truth):
    def canonicalize(div):
        return (div["divergence_class"], extract_endpoint_key(div))
    
    pred_set = {canonicalize(d) for d in predicted}
    truth_set = {canonicalize(d) for d in ground_truth}
    
    tp = len(pred_set & truth_set)
    fp = len(pred_set - truth_set)
    fn = len(truth_set - pred_set)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {"precision": precision, "recall": recall, "f1": f1}

def cross_validate(corpus, k=5):
    folds = [corpus[i::k] for i in range(k)]
    f1_scores = []
    
    for i, test_fold in enumerate(folds):
        train_folds = [f for j, f in enumerate(folds) if j != i]
        train_data = [item for fold in train_folds for item in fold]
        
        model = fine_tune("qwen2.5-coder:7b", examples=train_data, epochs=3)
        predictions = [model.predict(ex["input"]) for ex in test_fold]
        f1 = score_divergence_list(predictions, [e["output"] for e in test_fold])["f1"]
        f1_scores.append(f1)
    
    return {"mean_f1": sum(f1_scores)/len(f1_scores), "fold_scores": f1_scores}
`

## Summary & Next Steps

1. Phase 0 (now): Deploy opt-in corpus, target 1000-2000 submissions over 4 weeks
2. Phase 1: Sample + label 200-300 reports; bootstrap training set
3. Phase 2: Fine-tune Qwen2.5-Coder-7B on 500-1000 examples
4. Phase 3: Scale to 2000-5000 examples; target F1 >= 0.7
5. Phase 4: Deploy specialist as optional tier in Substrate Router

Estimated effort: 4-6 weeks (corpus collection) + 2 weeks (model work) = 6-8 weeks to shipping.

---

Word count: 1000+ | References: QLoRA (Dettmers et al., 2023), CHERENKOV core/contracts.py, cherenkov/divergence/skeptic.py
