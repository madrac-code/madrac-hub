# Phase 2 — Event Bus & Orchestration Layer

**Status**: PLANNED  
**Prerequisite**: Phase 1 complete ✅  
**Goal**: Design and implement a formal Event Bus for multi-component communication

---

## Context

Phase 1 delivered a concrete integration: SUBS ↔ DUBS via HTTP polling. This works, but it's not scalable to 5 components.

**Learnings from Phase 1:**
- HTTP + polling is sufficient for binary integrations (A→B)
- But 5-component ecosystem requires:
  - Async event broadcasting (1→N)
  - Decoupled message routing
  - Error recovery & retry logic
  - Status tracking across all components

**What we'll NOT do:**
- Don't implement a full distributed message queue (Kafka, RabbitMQ)
- Don't add external dependencies (keep it lightweight)
- Don't over-engineer before seeing concrete use cases

**What we WILL do:**
- Design abstraction from Phase 1 concrete implementation
- Implement Event Bus as local IPC (inter-process communication)
- Support 2–3 initial integrations (SUBS↔DUBS, others TBD)
- Document architecture, not just code

---

## Planned Scope

### Use Cases (ordered by priority)

1. **UC-001**: SUBS → DUBS (already works; will refactor to use Event Bus)
   - User clicks "Dub Now" → event published → DUBS listens → processes → publishes completion event → SUBS listens → displays result

2. **UC-002**: DUBS → Community Upload (future)
   - DUBS completes dubbing → publishes event → SUBS listens → shows "Save to community" button

3. **UC-003**: Community → SUBS Download (future)
   - User finds dubbed subtitle in community → publishes event → SUBS listens → imports subtitle

### Proposed Architecture

```
┌─────────────────────────────────────────────┐
│          Event Bus (IPC Layer)              │
│  ┌─────────────────────────────────────┐    │
│  │ Local Message Broker               │    │
│  │ (file-based or in-memory socket)   │    │
│  │                                     │    │
│  │ Topics:                             │    │
│  │  - dubbing.requested                │    │
│  │  - dubbing.completed                │    │
│  │  - dubbing.failed                   │    │
│  │  - subtitle.uploaded                │    │
│  │  - subtitle.downloaded              │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
	   ↑              ↑              ↑
	   │              │              │
	SUBS          DUBS        madrac-hub
  (publisher)   (subscriber)  (orchestrator)
				(publisher)
```

### Message Format (JSON)

```json
{
  "event_id": "uuid-here",
  "timestamp": "2026-07-01T14:30:00Z",
  "source": "madrac-subs",
  "event_type": "dubbing.requested",
  "payload": {
	"job_id": "uuid-here",
	"video_path": "/path/to/video.mp4",
	"srt_path": "/path/to/subs.srt",
	"config": {
	  "language": "es",
	  "voice": "female",
	  "high_quality": true
	}
  }
}
```

---

## Planned Implementation Steps

1. **Design Event Bus abstraction** (`event_bus.py`)
   - Publisher interface: `bus.publish(topic, payload)`
   - Subscriber interface: `bus.subscribe(topic, callback)`
   - Message queue (file-based or socket-based)

2. **Implement local IPC transport**
   - Option A: Unix domain socket (not on Windows) ❌
   - Option B: Named pipes (Windows only)
   - Option C: Local HTTP server (cross-platform, simplest)
   - Option D: Shared file queue (cross-platform, slower)
   - **Recommendation**: Option C (extend existing Flask/HTTP)

3. **Refactor SUBS → DUBS to use Event Bus**
   - Replace direct HTTP calls with `bus.publish("dubbing.requested", ...)`
   - Subscribe to `"dubbing.completed"` / `"dubbing.failed"` events
   - DUBS remains as HTTP responder (for now)

4. **Create madrac-hub orchestrator**
   - Central event listener (logs all events)
   - Handles retry logic, timeout management
   - Provides status dashboard

5. **Testing**
   - Unit tests for Event Bus (pub/sub, message ordering)
   - Integration tests for multi-component scenarios
   - Failure scenarios (component down, network lag, etc.)

---

## Architecture Decisions (TBD)

### Transport Layer
**Options:**
- A. HTTP long-polling (like Phase 1, but pub/sub)
- B. Local file queue (simple, cross-platform)
- C. Named pipes (Windows only)
- D. Custom binary protocol over TCP

**Recommendation**: Start with A (HTTP), extend if needed.

### Event Ordering
**Question**: Do events need strict ordering across all components, or just per-component?

**Decision**: Per-component ordering only (simplifies implementation).

### Persistence
**Question**: Should events persist to disk (e.g., for audit trail), or only in-memory?

**Decision**: In-memory first; add persistence in Phase 3 if needed.

### Error Handling
**Question**: If subscriber crashes, what happens to events?

**Decision**: Events are not persisted; subscriber must re-subscribe and poll for missed events.

---

## Backward Compatibility

- Phase 1 HTTP API (`POST /dubbing`, `GET /dubbing/<id>`) remains unchanged
- Event Bus is added **alongside** HTTP, not replacing it
- During transition, both interfaces work (SUBS can use either)
- After Phase 2, Event Bus becomes primary interface

---

## Success Criteria

Phase 2 is complete when:
1. ✅ Event Bus abstraction is documented and tested
2. ✅ IPC transport is working (HTTP or file-based)
3. ✅ SUBS → DUBS refactored to use Event Bus (UC-001)
4. ✅ madrac-hub orchestrator reads events and logs them
5. ✅ No breaking changes to Phase 1 functionality
6. ✅ Integration tests pass for multi-component scenarios

---

## Estimated Effort

- Design + implementation: 2–4 hours
- Testing + debugging: 2–3 hours
- Documentation: 1–2 hours
- **Total**: ~5–9 hours (one development session)

---

## Dependency on External Work

- Requires Phase 1 to be complete ✅ (SUBS↔DUBS working)
- No external API changes needed
- Can be developed independently in parallel if multiple developers available

---

## Known Risks

1. **Scope creep**: Event Bus design can become complex if we don't constrain to concrete use cases
   - **Mitigation**: Start with UC-001 only; add UC-002/UC-003 in Phase 3+

2. **Async complexity**: Multi-component async communication is error-prone
   - **Mitigation**: Start synchronous (blocking); add async if performance requires

3. **Windows compatibility**: Some IPC transports don't work on Windows
   - **Mitigation**: Choose HTTP (works everywhere) or test on Windows early

---

## Deferred to Phase 3+

- Cloud-based message broker (AWS SQS, GCP Pub/Sub)
- Real-time dashboard UI
- Advanced monitoring & alerting
- Integration with external systems
- Multi-machine deployment
