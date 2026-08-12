# MADRAC — Session Handover Template

Copy this, fill it in, and give it to the AI agent at the
start of every new session before any other instructions.

## Session Date: [DATE]

### State
Last commit: [hash — message]
Phase: [N — Name]
Exe built: [yes / needs rebuild]
MCP HTTP: [running on 7654 / not running]
Tests: [N passing]

### Completed Last Session
- [bullet 1]
- [bullet 2]

### Known Issues / Pending
- [bug or incomplete work]

### Objective This Session
[One clear goal]

### Files Agent Must Read First
- knowledge/STATE_OF_PROJECT.md
- knowledge/AI_READY_CODEBASE.md
- development/phases/PHASE_N_CURRENT.md
- knowledge/decisions/ADR_XXX.md (if relevant today)

### Active Constraints
- [constraint from ADR or LLAVE]
Example: Do not use sd.InputStream — use sd.rec() (LLAVE-005)
Example: Do not touch Supabase schema without ADR (ADR-002)

### Test Command
  cd D:\madrac-hub
  set PYTHONPATH=src\madrac_subs\src
  set QT_QPA_PLATFORM=offscreen
  pytest src/madrac_subs/tests/ --tb=short -q
Expected: 410+ passing.