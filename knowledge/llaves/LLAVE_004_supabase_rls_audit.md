# LLAVE: Supabase RLS Audit — 6 Vulnerabilities Found & Fixed

**Date**: 2026-07-02  
**Priority**: CRITICAL  
**Status**: RESOLVED (SQL script created, pending execution in Supabase Dashboard)

---

## Issue

Full audit of Supabase RLS policies revealed 6 security issues across the MADRAC community feature. ADR-002 had been open since 2026-06-04 with all action items unchecked.

---

## Findings

### 1. subtitles INSERT — User ID Spoofing
**Severity**: 🔴 CRITICAL  
**Before**: `WITH CHECK (auth.role() = 'authenticated')` — any authenticated user could insert rows with another user's `user_id`.  
**After**: `WITH CHECK (auth.uid() = user_id)` — can only insert as yourself.

### 2. subtitles UPDATE — No Policy
**Severity**: 🔴 HIGH  
**Before**: No UPDATE policy existed.  
**After**: `USING (auth.uid() = user_id)` — only owner can update.

### 3. subtitles DELETE — No Policy
**Severity**: 🟠 MEDIUM  
**Before**: No DELETE policy existed. Users could not remove their own content.  
**After**: `USING (auth.uid() = user_id)` — only owner can delete.

### 4. subtitles SELECT — Broken for Web
**Severity**: 🟠 MEDIUM  
**Before**: `USING (auth.role() = 'authenticated')` — the public-facing CommunityLibrary and download-srt route use `anon` role, so SELECT would fail for unauthenticated visitors.  
**After**: Published subtitles use `USING (status = 'published')` (public). Unpublished only visible to owner.

### 5. video_fingerprints — Conflicting Policies
**Severity**: 🟡 LOW  
**Before**: `migracion_fase3.sql` said `USING (true)`, `supabase_schema.sql` said `auth.role() = 'authenticated'`. Whichever ran last wins.  
**After**: Unified to `USING (true)` — fingerprints are non-sensitive metadata.

### 6. download_stats — Ghost Table
**Severity**: 🟠 MEDIUM  
**Before**: `track-app-download/route.ts` inserts into `download_stats`, but no schema or RLS defined anywhere in the repo.  
**After**: `CREATE TABLE IF NOT EXISTS` + RLS added to the fix script.

---

## Fix

Script: `D:\madrac-subs-web\supabase_rls_audit_fix.sql`

The script is idempotent (uses `DROP POLICY IF EXISTS` before `CREATE POLICY`). Execute in Supabase Dashboard > SQL Editor.

---

## Related

- ADR-002 (updated to RESOLVED)
- ADR-005 (web component inherits same risk)
- LLAVE_003 (serverless rate limiting — fixed in same batch)
- PHASES.md task 2.4 (security audit)

---

## Lesson

**Never ship community features with `auth.role() = 'authenticated'` as the only INSERT guard.** Always validate `auth.uid() = user_id` for any table where `user_id` determines ownership. The role check only confirms "someone is logged in", not "this is the right person."
