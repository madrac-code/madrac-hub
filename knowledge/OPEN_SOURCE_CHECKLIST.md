# MADRAC — Open Source Release Checklist

Track what needs to be done before public release.

## Documentation
  [x] AI_READY_CODEBASE.md
  [x] ADR registry (ADR-001 to ADR-011)
  [x] STATE_OF_PROJECT.md
  [x] CONTRIBUTING.md
  [x] SESSION_HANDOVER_TEMPLATE.md
  [ ] CHANGELOG.md (auto-generate from git log)
  [ ] API docs for MCP tools (auto-generate from tool_schemas.py)
  [ ] README per component (madrac-subs, madrac-dubs, madrac-asistente)
  [ ] Case study: "Building MADRAC with AI in 28 days"

## Security (required before public)
  [ ] ADR-002: Supabase RLS isolation tests + pentest
  [ ] Audit all files for hardcoded secrets
  [ ] Confirm config.json (user data) never in git history
  [ ] MUI whitelist audit: no arbitrary code execution possible

## Code Quality
  [ ] Test coverage >= 60% (currently ~40%)
  [ ] All TODOs documented in AI_READY_CODEBASE.md or ADRs
  [ ] scipy decision: bundle in spec or remove from record_segment

## Licensing
  [ ] Choose license (MIT recommended)
  [ ] LICENSE file in all repos
  [ ] Dependency license audit
  [ ] Credits: openWakeWord, faster-whisper, Demucs, Edge TTS, MarianMT

## Community
  [ ] GitHub Issues templates
  [ ] GitHub Discussions enabled
  [ ] MUI community templates in madrac-subs-web (Phase 3)

## Methodology (most valuable contribution)
  [x] CONTEXT_ENGINEERING.md
  [x] AI_COLLABORATION.md
  [x] ADR process
  [ ] Prompt templates in development/prompts/
  [ ] Published case study