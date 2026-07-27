"""
hack/reporting
---------------
Downloadable artefacts derived from a ServiceAuditReport:

* PdfReporter       — enterprise-styled PDF (reportlab)
* SkillMdGenerator  — compact SKILL.md an AI agent can ingest
"""

from __future__ import annotations

from .pdf import PdfReporter
from .skill_md import SkillMdGenerator

__all__ = ["PdfReporter", "SkillMdGenerator"]
