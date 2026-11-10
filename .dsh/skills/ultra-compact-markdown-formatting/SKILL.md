---
name: ultra-compact-markdown-formatting
description: "Always format Markdown files in ultra-compact form - remove decorative dividers and blank vertical lines between headers and blocks, and consolidate the navigation header into a single inline index for high readability and compact presentation. Use when creating or editing any Markdown file to keep output dense, scannable, and free of decorative whitespace."
category: utilities
---

# Ultra-Compact Markdown Formatting

## Overview

When creating or editing any Markdown (`.md`) file, keep the output ultra-compact: minimal vertical whitespace, no decorative dividers, and a single inline navigation index. The goal is high readability without wasted space.

## When to use

- Creating any new Markdown (`.md`) document or runbook.
- Editing, refactoring, or updating existing Markdown files.
- Removing decorative dividers and blank vertical lines between headers and blocks.
- Consolidating navigation headers into a single inline index.

## Guidelines

- **Removed decorative dividers and blank vertical lines between headers and blocks:** Strip horizontal rules (`---`) and extra blank lines so headers and the blocks that follow them are separated by at most a single blank line.
- **Consolidated the navigation header into a single inline index for high readability and compact presentation:** Fold navigation headers into a single inline index of links instead of splitting navigation into separate header and index blocks.

## Practical workflow

1. Remove decorative dividers and blank vertical lines between headers and blocks.
2. Consolidate the navigation header into a single inline index.
3. Run a final whitespace, divider, and navigation audit before saving.

## Common pitfalls

- Leaving decorative `---` dividers or double blank lines between headers and blocks.
- Splitting navigation into separate header and index blocks instead of one inline index.
