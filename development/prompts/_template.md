# Prompt Template — [Task Name]

**Component**: [SUBS | ASISTENTE | DUBS | HUB]  
**Task type**: [feature | fix | refactor | documentation | analysis]  
**AI recommended**: [Claude | GPT | Gemini | OpenCode | any]  
**Context required**: [list which context files to include]

---

## Context Layer 1 — Project Identity

MADRAC is a Python desktop multimedia suite with 4 components:
- SUBS: subtitle engine (PySide6, Whisper, MarianMT)
- ASISTENTE: voice assistant (Ollama, Whisper, PowerShell TTS)
- DUBS: dubbing engine (Flask API, Edge TTS)
- HUB: coordinator and knowledge base

Current phase: [PHASE NUMBER AND NAME]
Active constraints: [list from current ADRs]

---

## Context Layer 2 — Component State

[Paste relevant file structure]
[Paste last 5 git commits]
[Paste relevant ADRs]

---

## Context Layer 3 — Task

**Problem**: [specific problem description]
**Tried already**: [what has been attempted]
**Must NOT change**: [explicit constraints]
**Expected output**: [code | documentation | analysis | plan]

---

## Context Layer 4 — AI Role

Your role in this session: [implementer | analyst | reviewer | designer]
You CAN decide: [specific decisions delegated to AI]
You must PROPOSE (not decide): [decisions requiring human approval]
