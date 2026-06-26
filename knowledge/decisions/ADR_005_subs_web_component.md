# ADR-005 — madrac-subs-web as Fifth Ecosystem Component

**Date**: 2026-06-26
**Status**: Accepted
**Deciders**: Human
**Components affected**: SUBS-WEB, HUB

## Context

During Phase 0 documentation, it was discovered that a fifth component
existed but was not registered in the ecosystem map. madrac-subs-web
is the web frontend for MADRAC-SUBS, deployed on Vercel and connected
to the same Supabase instance as the desktop component.

This component was active during MADRAC-SUBS v2 and allowed users to
authenticate via Google OAuth and share/search subtitles from a browser.

## Component Details

| Property | Value |
|----------|-------|
| Location | `D:\madrac-subs-web` |
| Repository | github.com/madrac-code/madrac-subs-web |
| Deployment | https://madrac-subs.vercel.app |
| Stack | Vercel + Supabase (PostgreSQL + Auth + Storage) |
| Auth | Google OAuth |
| Shared backend | Same Supabase instance as madrac-subs desktop |
| Status | Functional, no active users as of 2026-06-26 |

## Why This Matters

The web component shares the Supabase backend with the desktop component.
This means:
- Any RLS vulnerability affects both surfaces simultaneously
- Schema changes in Supabase affect both components
- User data is shared across desktop and web

## Active Risks

### RLS Insufficiency (inherited from ADR-002)
The same Supabase RLS risk documented in ADR-002 applies to this
component. A user authenticated via the web could potentially access
subtitle data belonging to other users.

**Current status**: Not urgent — no active users.
**Required before public launch**: Full RLS audit covering both
desktop API calls and web API calls as separate attack surfaces.

## Decision

Register madrac-subs-web as an official fifth component of the
MADRAC ecosystem. Document it in all relevant ecosystem maps.
Apply the same development standards as other components.

## Lessons Learned

Components that exist but are not documented are invisible to the
ecosystem. Any component with a git repository, a deployment, or
a shared backend dependency must be registered in HUB immediately
upon discovery — not retroactively.

**Rule added**: When a new component is created or discovered,
the first action is to add it to HUB README and create its ADR.
Before writing any code.
