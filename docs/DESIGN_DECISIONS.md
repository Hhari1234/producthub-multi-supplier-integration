# Design Decisions

## Why this architecture

ProductHub separates ingestion, validation, standardization, matching, and publishing into clear service layers to keep the business logic understandable and testable.

## Deterministic matching

Matching is based on explicit priorities rather than probabilistic logic. This keeps the process explainable and reproducible for operators.

## Data quality as a first-class workflow

Rejected records are stored instead of being silently dropped to maintain traceability and support investigation.

## Idempotent ingestion

The source_record_key is used to avoid duplicate raw rows across reruns.

## Conflict policy

The selected product value is chosen with a deterministic rule set rather than arbitrary last-write-wins behavior.
