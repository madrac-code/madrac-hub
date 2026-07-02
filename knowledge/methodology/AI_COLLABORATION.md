# AI Collaboration Model — MADRAC

## The Human Role

The human developer in MADRAC acts as:

1. **Vision holder** — defines what the ecosystem should become
2. **Arbitrator** — decides between competing AI proposals
3. **Quality gate** — reviews, tests, and commits all generated code
4. **Context engineer** — prepares and maintains the context stack
5. **Risk manager** — identifies when AI is reproducing bad assumptions

The human does NOT need to write every line of code. The human DOES need to understand every line of code that ships.

## The AI Role

AI agents in MADRAC act as:

1. **Implementation partners** — generate code from well-defined specs
2. **Documentation generators** — produce structured documentation
3. **Analysis tools** — identify patterns, risks, and alternatives
4. **Debugging assistants** — analyze errors when given full context

AI agents do NOT make architectural decisions. AI agents do NOT commit code directly. AI agents do NOT define what the project should become.

## Known AI Failure Modes in This Project

### Assumption Reproduction
If the prompt contains a technical assumption (e.g., "use PyInstaller"), the AI will use it without questioning whether it's appropriate.
**Mitigation**: Explicitly ask for alternatives before accepting a solution.

### Architectural Hallucination
AI can produce coherent, plausible architectural documentation that contains invalid assumptions about how components interact.
**Mitigation**: Validate designs against real code before treating as authoritative.

### Context Blindness
Each AI session starts from zero. Without explicit context, the AI will make reasonable but potentially inconsistent assumptions.
**Mitigation**: Always include Layer 1 + Layer 2 context (see CONTEXT_ENGINEERING.md).

### Documentation as Completion
AI produces documentation easily, which can create a false sense of progress. A 500-line ARCHITECTURE.md is not a working Event Bus.
**Mitigation**: Measure progress in working code, not in documentation lines.

## Session Checklist

Before every development session with an AI agent:

- [ ] Is the context stack prepared? (Layers 1-4)
- [ ] Are the relevant ADRs included in the context?
- [ ] Is the current phase document up to date?
- [ ] Have I defined what the AI can decide vs. what it must propose?
- [ ] Have I specified what must NOT change in this session?

After every development session:

- [ ] Was any architectural decision made? → Write an ADR
- [ ] Was any known bad pattern avoided? → Update relevant ADR
- [ ] Did the AI reproduce a bad assumption? → Document in postmortems
- [ ] Are context files still accurate? → Update if needed
- [ ] Did I commit? → Always commit before ending the session
