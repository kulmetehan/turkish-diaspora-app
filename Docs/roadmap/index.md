---
title: Roadmap Artifacts Index
status: active
last_updated: 2025-01-15
scope: roadmap, planning
owners: [tda-core]
---

# Roadmap Artifacts Index

This document provides an index of all roadmap-related artifacts in the repository and explains their relationships and purposes.

## Canonical Roadmap Artifacts

### Markdown Documents

| Document | Purpose | Status | Last Updated |
|----------|---------|--------|--------------|
| [`Docs/Roadmap.md`](../Roadmap.md) | High-level startup masterplan and vision document | Active | 2025 |
| [`Docs/Roadmap_Backlog.md`](../Roadmap_Backlog.md) | Jira import-ready CSV backlog with all epics and stories | Active | 2025-01-15 |
| [`PROJECT_PROGRESS.md`](../../PROJECT_PROGRESS.md) | Progress log tracking delivered capabilities and current focus | Active | 2025-01-15 |
| [`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md) | Architecture overview and current phase narrative | Active | 2025-01-15 |

### CSV/Data Files

| File | Purpose | Format | Status |
|------|---------|--------|--------|
| [`Docs/Roadmap_Backlog.md`](../Roadmap_Backlog.md) | Jira import-ready backlog | CSV (Markdown table) | Active - Use for Jira imports |
| [`Docs/Roadmap_Backlog.archived.csv`](../Roadmap_Backlog.archived.csv) | Archived backlog with "Epic Name" column | CSV | Archived - Legacy format |
| [`Docs/Jira Import.csv`](../Jira%20Import.csv) | Additional Jira import file | CSV | Unknown status |

## Document Relationships

```
Roadmap.md (Vision & Masterplan)
    ↓
    ├─→ Roadmap_Backlog.md (Jira-ready backlog)
    │       └─→ Follows template: Docs/templates/4)jira_import.md
    │
    ├─→ PROJECT_PROGRESS.md (Delivered capabilities)
    │       └─→ References: Roadmap_Backlog.md
    │
    └─→ PROJECT_CONTEXT.md (Architecture & current phase)
            └─→ References: PROJECT_PROGRESS.md
```

## Roadmap Formats

### 1. Roadmap.md (Vision Document)

**Purpose**: High-level strategic vision and masterplan
- Contains startup vision, architecture overview, and strategic goals
- Written in narrative format
- Updated periodically to reflect strategic direction

**Use When**: 
- Understanding overall project vision
- Strategic planning discussions
- Stakeholder alignment

### 2. Roadmap_Backlog.md (Jira Import Format)

**Purpose**: Detailed backlog ready for Jira import
- Contains all epics and stories in Jira-compatible CSV format
- Uses Parent/Issue ID model (no Epic Name column)
- Follows template: [`Docs/templates/4)jira_import.md`](../templates/4)jira_import.md

**Format**:
- CSV with columns: `issue type,summary,description,status,priority,labels,story points,issue id,parent,acceptance criteria,definition of done,technical notes,risk level`
- Epics have `parent` = (empty), `issue id` = unique number
- Stories have `parent` = epic issue id

**Use When**:
- Importing backlog into Jira
- Tracking detailed story-level progress
- Planning sprint work

**Import Instructions**: See [`Docs/templates/4)jira_import.md`](../templates/4)jira_import.md

### 3. PROJECT_PROGRESS.md (Progress Log)

**Purpose**: Tracks delivered capabilities and current focus
- Timeline highlights
- Delivered capabilities summary
- Current focus items
- Recent changes log

**Use When**:
- Understanding project maturity
- Communicating status to stakeholders
- Tracking epic completion

### 4. PROJECT_CONTEXT.md (Architecture Context)

**Purpose**: Concise narrative of platform architecture and current phase
- System architecture overview
- High-level data flow
- Current phase description
- Core components and directories

**Use When**:
- Onboarding new contributors
- Understanding system architecture
- Aligning stakeholders

## Legacy/Archive Files

### Roadmap_Backlog.archived.csv

**Status**: Archived
**Reason**: Contains "Epic Name" column which is deprecated in Jira Cloud
**Replacement**: [`Docs/Roadmap_Backlog.md`](../Roadmap_Backlog.md) (new format)

**Note**: Kept for historical reference. Do not use for Jira imports.

## Jira Import Process

1. **Prepare Backlog**: Use [`Docs/Roadmap_Backlog.md`](../Roadmap_Backlog.md)
2. **Follow Template**: Reference [`Docs/templates/4)jira_import.md`](../templates/4)jira_import.md)
3. **Import to Jira**: Use Jira CSV import wizard
4. **Verify Hierarchy**: Ensure parent-child relationships are correct

**Important**: The backlog uses the Parent/Issue ID model. Do NOT use "Epic Name" column.

## Document Maintenance

### When to Update

- **Roadmap.md**: When strategic vision or architecture changes significantly
- **Roadmap_Backlog.md**: When adding new epics/stories or updating status
- **PROJECT_PROGRESS.md**: When epics complete, major milestones reached, or current focus changes
- **PROJECT_CONTEXT.md**: When architecture, hosting, or strategic focus changes

### Update Frequency

- **Roadmap.md**: Quarterly or when major strategic shifts occur
- **Roadmap_Backlog.md**: Continuously as work progresses
- **PROJECT_PROGRESS.md**: After each epic completion or major milestone
- **PROJECT_CONTEXT.md**: When architecture or phase changes

## Related Documentation

- [`Docs/templates/4)jira_import.md`](../templates/4)jira_import.md) - Jira import template and guidelines
- [`PROJECT_PROGRESS.md`](../../PROJECT_PROGRESS.md) - Progress tracking
- [`PROJECT_CONTEXT.md`](../../PROJECT_CONTEXT.md) - Architecture context
- [`Docs/README.md`](../README.md) - Documentation index

