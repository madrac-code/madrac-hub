# ADR-002 — Supabase Community Backend with Insufficient RLS

**Date**: 2026-06-04 (implemented), 2026-06-26 (documented as risk)  
**Status**: OPEN RISK — must be resolved before public launch  
**Deciders**: Human  
**Components affected**: SUBS (community feature)

## Context

MADRAC-SUBS v3 includes a community feature: users can share and search subtitles, authenticated via Google OAuth. Supabase was chosen as the backend (PostgreSQL + Auth + Storage).

## Decision

Supabase was implemented quickly as part of the community phase (4 June, commits bc3f39a and deaca1d). RLS policies were added but later identified as insufficient.

## Consequences

### Negative
- A user may be able to access subtitle data belonging to other users
- This is a real privacy vulnerability affecting real users
- Documented in PHASES.md as critical risk, unresolved as of rc1

## Required Action Before Public Launch

- [ ] Audit all RLS policies against each API endpoint
- [ ] Add integration tests that verify cross-user data isolation
- [ ] Penetration test the community endpoints
- [ ] Do NOT promote the community feature until this is resolved

## Lessons Learned

Security policies on community features must be validated before rc, not after. The correct phase: implement RLS → write isolation tests → release community feature.
