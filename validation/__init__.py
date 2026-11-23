"""Deterministic validation of extracted quote drafts (docs/05-ingestion-pipeline.md, stage 5).

No AI here: the same draft always gives the same result. Problems become flags
for review rather than errors, so a draft is never lost.
"""
