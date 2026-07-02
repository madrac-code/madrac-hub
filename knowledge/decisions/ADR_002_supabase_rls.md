# ADR-002 — Supabase Community Backend with Insufficient RLS

**Date**: 2026-06-04 (implemented), 2026-06-26 (documented as risk), 2026-07-02 (audited & resolved)  
**Status**: RESOLVED  
**Deciders**: Human  
**Components affected**: SUBS (community feature), SUBS-WEB

## Context

MADRAC-SUBS v3 includes a community feature: users can share and search subtitles, authenticated via Google OAuth. Supabase was chosen as the backend (PostgreSQL + Auth + Storage).

## Decision

Supabase was implemented quickly as part of the community phase (4 June, commits bc3f39a and deaca1d). RLS policies were added but later identified as insufficient.

## Audit (2026-07-02) — LLAVE_004

A full audit was conducted. Findings:

1. **subtitles INSERT**: Policy only checked `auth.role() = 'authenticated'` — any user could insert with another user's `user_id`. **FIXED**: `WITH CHECK (auth.uid() = user_id)`
2. **subtitles UPDATE/DELETE**: No policies existed. **FIXED**: Owner-only policies added.
3. **subtitles SELECT**: Required `authenticated` role, but web showed library publicly. **FIXED**: Published subtitles readable by anyone; unpublished only by owner.
4. **download_stats**: Table used by web but never defined in schema. **FIXED**: Schema + RLS added.
5. **video_fingerprints SELECT**: Conflicting policies between migration files. **FIXED**: Unified to `USING (true)`.
6. **Storage**: `subtitle-files` bucket marked public in original schema. **FIXED**: Set to private + authenticated-only policies.

Fix script: `madrac-subs-web/supabase_rls_audit_fix.sql`

## Consequences

### Positive (post-fix)
- Users can only insert/update/delete their own subtitles
- Published subtitles are publicly readable (community feature works without login)
- Storage is private (requires auth session or signed URLs)
- All tables have RLS enabled with appropriate policies

### Negative (historical)
- A user could have inserted subtitle data with another user's `user_id` (no evidence of exploitation, no active users as of audit date)
- This risk was documented for ~1 month before being resolved

## Required Action Before Public Launch

- [x] Audit all RLS policies against each API endpoint
- [ ] Add integration tests that verify cross-user data isolation
- [ ] Penetration test the community endpoints
- [x] Do NOT promote the community feature until this is resolved

## Lessons Learned

Security policies on community features must be validated before rc, not after. The correct phase: implement RLS → write isolation tests → release community feature.
