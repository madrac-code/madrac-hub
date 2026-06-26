# Context Engineering — The MADRAC Development Methodology

## What is Context Engineering?

Context Engineering is the practice of deliberately designing, preparing, and managing the information that AI agents receive in order to produce reliable, consistent, and high-quality outputs.

In traditional software development, the bottleneck is writing code. In AI-assisted development, the bottleneck is preparing the right context.

## The MADRAC Context Stack

Each development session should have a clear context stack:

### Layer 1 — Project Identity (always included)
- What is MADRAC? What is this component?
- What is the current phase?
- What are the active constraints? (e.g., no PyInstaller, pin deps)

### Layer 2 — Component State (task-specific)
- Current file structure
- Recent commits (last 5-10)
- Active known bugs or risks
- Relevant ADRs

### Layer 3 — Task Context (session-specific)
- What specific problem needs to be solved?
- What has already been tried?
- What must NOT be changed?
- What is the expected output format?

### Layer 4 — AI Role Definition
- Which AI is being used and why?
- What is its specific role in this session?
- What decisions does it have authority to make vs. propose?

## The Arbitration Pattern

MADRAC development frequently involves querying multiple AI models and synthesizing their responses. The human acts as arbitrator:

1. Define the problem clearly
2. Query 2-3 AI models independently
3. Compare responses — note agreements and conflicts
4. Synthesize: take the best elements of each
5. Document which AI proposed what (in ADRs when significant)

This pattern prevents single-model bias and produces better solutions than any individual model would produce alone.

## Context Staleness — The Biggest Risk

As the project grows, context files become outdated. An AI working from stale context will generate inconsistent code.

Rules to prevent context staleness:
- Update context files BEFORE starting a new session, not after
- Context files are living documents, not snapshots
- When a major decision changes the architecture, update all affected context files in the same commit

## Files That Are Always Context

These files must be kept current at all times:
- `knowledge/architecture/MADRAC_CORE_DESIGN.md` — system architecture
- `development/phases/PHASE_N_CURRENT.md` — current phase status
- `knowledge/decisions/` — all ADRs

## Anti-Patterns to Avoid

- **Assumption reproduction**: If your prompt mentions PyInstaller, the AI will use PyInstaller. Be explicit about constraints.
- **Single-session blindness**: AI has no memory of previous sessions. Never assume it knows the project state.
- **Documentation as progress**: A 757-line design document is not an implementation. Distinguish design artifacts from working code.
