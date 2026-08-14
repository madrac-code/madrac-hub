# ADR-014: RECON Character Identity — speaker_id → character_id mapping

## Status
Accepted

## Context
RECON Phase 1 produced `speakers.json` (acoustic identity: `speaker_id`, `name`, turn segments).
RECON Phase 2 produced `speaker_segments.json` (subtitle segments linked to speakers with confidence).

Downstream modules (Storyboard, Dubbing Station, Animation) need a **stable narrative/visual identity** that is distinct from the acoustic identity. A character may:
- Exist before any speaker is assigned (pre-production)
- Be mapped to a speaker later
- Have multiple speakers over time (e.g., different actors for same character)
- Have visual references, notes, and other narrative attributes

The acoustic identity (`speaker_id`) and narrative identity (`character_id`) must be **decoupled**.

## Decision
Add a new independent artifact `characters.json` in the workspace, with MCP tools for CRUD and mapping.

### characters.json schema
```json
{
  "schema_version": "1.0",
  "job_id": "sha256-...",
  "characters": [
    {
      "character_id": "char_01",
      "name": "Lina",
      "speaker_id": "speaker_1",
      "visual_reference": null,
      "notes": ""
    }
  ]
}
```

### Rules
- `character_id`: stable within workspace (e.g., `char_01`, `char_02`...)
- `speaker_id`: optional, nullable — character can exist without speaker
- `name`: editable, narrative name
- `visual_reference`: optional, for future image generation reference
- `notes`: optional, free text
- **No modification** of `speakers.json`, `segments.json`, `speaker_segments.json`
- One speaker → at most one character at a time (current mapping)
- One character → at most one speaker at a time
- Reassignment updates the current mapping; history preserved in notes if needed

### MCP Tools
1. `list_characters(job_id)` — returns all characters with current mapping
2. `set_character(job_id, character_id, name, visual_reference=None, notes="")` — create/update character
3. `map_speaker_to_character(job_id, speaker_id, character_id)` — link acoustic to narrative

### Metadata updates
`metadata.json` → `artifacts.characters: true`, `characters_json_path`, `character_count`

## Rationale
- **Separation of concerns**: Acoustic (RECON) vs Narrative (Character Identity) are different domains with different lifecycles
- **Independent artifact**: `characters.json` doesn't touch existing JSONs — SUBS/DUBS/RECON consumers unaffected
- **Extensible**: `visual_reference` and `notes` ready for Storyboard/Animation without schema changes
- **MCP-first**: Tools follow existing pattern (22→25 tools), usable by LLM agents and UI

## Consequences
- New artifact: `characters.json` per job
- New MCP tools: 3 tools (total 25)
- Phase 3 (Storyboard) will consume `characters.json` + `speaker_segments.json`
- Dubbing Station will use `character_id` → TTS voice mapping

## Out of Scope
- Voice cloning / TTS voice assignment (future)
- Storyboard JSON schema (separate ADR)
- Image generation / IP-Adapter / ControlNet
- Multi-speaker per character history (can be added later via `notes` or new field)

## Future Compatibility
This contract enables:
```
character_id → visual_reference → storyboard → image/video generation
character_id → speaker_segments → dubbing per character (TTS voice per character)
```