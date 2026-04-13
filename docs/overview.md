# GeoSAM + Nexus — Portfolio Strategy Overview

**Date:** 2026-04-12  
**Author:** Sainatha Yatham

---

## The One-Paragraph Version

You are building two connected projects to close the gap from SRE → full AI/MLOps engineer. GeoSAM is an open source Python toolkit that applies Meta's Segment Anything Model to seismic data interpretation — it generates high-quality geological feature masks without any training data, releases them to the geoscience community, and directly leverages your 8 years of domain expertise at Borehole Seismic. Nexus is the enterprise MLOps platform that consumes GeoSAM's output: it takes those masks as training labels, fine-tunes a lightweight production model, serves it through a production API gateway, and monitors its quality using SLOs and error budgets — the same SRE framework you know applied to model reliability instead of system reliability. Together they cover everything a senior AI/MLOps engineer role requires: training pipelines, model registries, serving infrastructure, eval gates in CI/CD, observability, drift detection, and auto-rollback.

---

## Why These Two Projects Together

### The gaps they close

| Gap | Before | After GeoSAM + Nexus |
|-----|--------|----------------------|
| GPU inference/serving | API calls only | vLLM-equivalent serving via BentoML + Modal |
| Model training | None | LoRA fine-tuning, MLflow, DVC |
| Eval discipline | None | RAGAS equivalent (IoU/Dice gates), CI eval workflow |
| SRE applied to AI | Concept only | Error budgets on IoU, auto-rollback, drift detection |
| Open source credibility | None | Community-adopted PyPI package |
| Full product | Flask tools | Next.js + FastAPI enterprise app |
| MLOps infrastructure | Mentioned in CV | Demonstrated: K8s, Helm, Terraform, GitHub Actions |

### Why the domain matters

You are not building another incident intelligence platform or another chatbot RAG system. You are building in geoscience AI — a domain where you have genuine expertise no one can fake. When you walk into an interview at AlphaSense (financial data AI), Akuity (GitOps/K8s), or any MLOps platform company, you have:

1. Real domain knowledge (seismic interpretation, borehole data, SLAs)
2. Real production experience (Veritas Seismic, $10K/month, 20-person team)
3. An open source tool the geoscience community uses
4. An enterprise platform that demonstrates the full MLOps lifecycle

No other candidate in your search has all four. Most have none.

---

## The Interview Story

### For MLOps Engineer roles

> "I built a two-project system: an open source geoscience AI toolkit called GeoSAM, and an enterprise MLOps platform called Nexus. GeoSAM uses Meta's Segment Anything Model zero-shot to generate geological feature masks from seismic data — no training data required, because SAM generalizes from 1 million natural images. Those masks became my training labels for Nexus, which fine-tunes a production segmentation model, serves it through a BentoML gateway with A/B routing, and monitors quality via SLOs. The interesting part is the SLO design: I applied error budgets not to system uptime but to model IoU — if the production model's intersection-over-union drops below 0.78 for two consecutive weekly evals, the error budget is exhausted and auto-rollback triggers. Same mental model as SRE, applied to model quality."

### For AI SRE roles

> "The project that best represents my thinking is the observability layer I built in Nexus. I defined three SLOs: p95 inference latency under 3 seconds, production model IoU above 0.78, and low-confidence prediction rate below 5%. Each has an error budget with burn rate alerts. When the low-confidence rate SLO fires, it means users are getting uncertain predictions — which is the AI equivalent of elevated error rates. The alert triggers before users notice, exactly how good SRE works. I also implemented drift detection using Population Stability Index on input attribute distributions, because a model can be healthy on its training distribution and fail silently on new geological settings. That silent failure is the hardest thing to catch."

### For AI Engineer roles

> "I implemented the training pipeline end-to-end: LoRA adapters on EfficientSAM's image encoder, PyTorch mixed precision, combined BCE + Dice loss, MLflow experiment tracking with full hyperparameter logging, and an eval gate in CI that blocks deployment if IoU falls below threshold. The fine-tuned model runs in 180ms per slice versus 2500ms for base SAM2 — a 14x speedup — because it is specialized for geological boundaries and 10x smaller. The training data came from my open source tool GeoSAM, which generates masks using zero-shot SAM2. So the pipeline is: foundation model generates labels → supervised training on those labels → production deployment of the lightweight model. That is the correct production ML loop."

---

## Timeline Summary

```
Week 1  GeoSAM: SEG-Y I/O + seismic attribute computation
Week 2  GeoSAM: SAM2 integration + SOM clustering + MLflow
Week 3  GeoSAM: Gradio UI + Docker
Week 4  GeoSAM: Tests + CI/CD + PyPI release + community post
        Nexus:  Docker Compose local stack + Terraform + Helm skeleton
Week 5  Nexus:  Training pipeline + MLflow + model registry
Week 6  Nexus:  BentoML serving + FastAPI gateway + A/B routing
Week 7  Nexus:  App API + Next.js frontend (minimal)
Week 8  Nexus:  Observability + Prometheus + Grafana + SLOs
Week 9  Nexus:  GitHub Actions CI/CD + eval gates + GKE deploy
Week 10 Both:   Demo video + blog post + portfolio update
```

---

## Files in This Repository

```
geosam/
├── docs/
│   ├── overview.md         ← this file
│   └── PRD.md              ← full product requirements document
(source code to be added as project is built)

nexus/
├── docs/
│   └── PRD.md              ← full product requirements document
(source code to be added as project is built)
```

---

## Key Decisions Already Made

**On the data problem:** GeoSAM uses SAM2 zero-shot — no training data needed. Nexus uses GeoSAM masks as labels — the labeling cost is the GeoSAM run, not human annotation. Data is not a bottleneck.

**On GPU:** Modal.com serverless GPU (~$0.10/hr A10G). No local GPU required. No permanent cluster cost. Total training budget: ~$15–25 for portfolio purposes.

**On scope:** Both projects are production-quality but not infinite. GeoSAM v0.1.0 supports F3 Netherlands dataset and basic SOM clustering. Nexus v1.0.0 is single-tenant with simplified auth. The infrastructure patterns are enterprise-grade even if the product scope is controlled.

**On the open source first approach:** Release GeoSAM before building Nexus. Community feedback and stars on GeoSAM validate the domain and give you something to reference when describing Nexus. Sequence matters.
