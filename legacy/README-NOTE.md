# Why this code is in legacy/

This directory contains OpenSteps v1.0: a hosted authorization gateway (FastAPI +
PostgreSQL) with a Next.js audit dashboard, where agents signed HTTP requests to a
central API.

The thesis v2.0 (`docs/OpenSteps_Final.md`) supersedes that architecture. Phase 0 is
deliberately *not* a hosted service: it is an MCP proxy that emits signed,
hash-chained receipts to the customer's own storage, plus a standalone offline
verifier. See the repository root for the current implementation.

The v1.0 code is kept for reference — its canonical-JSON, Merkle checkpoint, and
approval-scoping ideas inform later roadmap phases (Rung 2 anchoring, hosted tier).
It is unmaintained and its README describes the old architecture.
