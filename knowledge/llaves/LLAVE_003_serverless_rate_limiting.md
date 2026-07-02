# LLAVE: Serverless Rate Limiting & Memory Leaks in Next.js

**Date**: 2026-07-02
**Priority**: HIGH
**Status**: IDENTIFIED

---

## Issue

En el proyecto `madrac-subs-web`, los endpoints de la API (`app/api/download-srt/route.ts` y `app/api/track-download/route.ts`) implementan un sistema de *Rate Limiting* manual utilizando variables globales (`Map`) y temporizadores (`setInterval`):

```typescript
const hits = new Map<string, number[]>()

function cleanupStale() {
  // ... limpieza del Map ...
}

setInterval(cleanupStale, CLEANUP_INTERVAL)
```

---

## Root Cause

Este enfoque tiene dos problemas graves de deuda técnica (Technical Debt) en un entorno Serverless (como Vercel o Next.js API Routes):

1. **Estado Efímero y Aislamiento**: Las variables globales (`Map`) no se comparten entre diferentes instancias de las Serverless Functions. Si la plataforma escala la función a 10 contenedores distintos, el límite de peticiones (Rate Limit) será independiente en cada uno, permitiendo que un usuario exceda el límite fácilmente si sus peticiones son ruteadas a diferentes instancias. Además, en los cold starts, el estado se pierde.
2. **Fugas de Memoria (Memory Leaks)**: El uso de `setInterval` en un entorno Serverless es un antipatrón. El runtime puede pausar o terminar la ejecución del contenedor en cualquier momento, dejando el timer inactivo o provocando que el contenedor no pueda cerrarse limpiamente (zombie processes).

---

## Solution (Propuesta)

Se debe reemplazar la implementación de Rate Limiting en memoria por una solución distribuida:

1. **Upstash Redis / KV Store**: Utilizar `@upstash/ratelimit` junto con una base de datos Redis (o Vercel KV) para mantener el contador de peticiones de manera centralizada y persistente.
2. **Eliminar `setInterval`**: Al usar Redis con expiración automática (TTL) o librerías optimizadas para Edge/Serverless, ya no es necesario el ciclo continuo de recolección de basura manual.

---

## Action Items

- [ ] Integrar un almacén Key-Value o Redis (por ejemplo, Vercel KV o Upstash).
- [ ] Refactorizar `app/api/download-srt/route.ts` para usar la solución KV.
- [ ] Refactorizar `app/api/track-download/route.ts` (y otras rutas similares) para usar la solución KV.
- [ ] Eliminar todo rastro de `setInterval` y variables globales tipo `Map`.
