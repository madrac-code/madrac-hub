# ADR-003 — Git Discipline: Every Component Must Have Version History

**Date**: 2026-06-26  
**Status**: Accepted — mandatory for all future components  
**Deciders**: Human  
**Components affected**: ALL

## Context

MADRAC-DUBS was created on 2026-06-25 without git initialization. The component was likely generated in a single AI-assisted session and uploaded without intermediate commits. This makes it impossible to audit changes, roll back, or understand the evolution of the component.

## Decision

Every MADRAC component, from its first file, must have:
1. A git repository initialized before any code is written
2. A remote configured on github.com/madrac-code/
3. At minimum one commit per working session

## Rules (mandatory)

- [ ] `git init` + `git remote add` = first action in any new component directory
- [ ] Never generate and upload a component without commit history
- [ ] AI-generated code must go through: generate → review → commit, not generate → upload
- [ ] If a session produces significant changes with no commits, create a retrospective commit with a clear message before the next session

## Lessons Learned

The workflow "prompt → code → commit" must never skip the last step. When AI generates an entire component in one session, the temptation is to upload it directly. Resist this. The commit history IS the audit trail.
