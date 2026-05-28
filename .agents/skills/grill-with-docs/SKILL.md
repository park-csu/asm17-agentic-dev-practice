---
name: grill-with-docs
description: Stress-tests a plan against existing domain terminology and documented decisions, then updates CONTEXT.md and ADRs as decisions crystallize. Use when the user wants a structured grilling session for a feature plan, architecture choice, or domain model clarification.
license: MIT
---

# Grill With Docs

Use this skill to interview the user about a plan until the domain language, design branches, and decision dependencies are clear.

## Core workflow

- Ask questions one at a time, waiting for the user's answer before continuing.
- For each question, provide your recommended answer.
- If a question can be answered by exploring the codebase, explore the codebase instead of asking.
- Walk down each branch of the design tree and resolve dependencies between decisions one by one.
- Challenge vague, overloaded, or conflicting terms against the repository's documented domain language.
- Update documentation inline as terms and decisions crystallize.

## Domain awareness

During codebase exploration, also look for existing documentation.

Most repositories have a single context:

```text
/
├── CONTEXT.md
├── docs/
│   └── adr/
│       ├── 0001-event-sourced-orders.md
│       └── 0002-postgres-for-write-model.md
└── src/
```

If `CONTEXT-MAP.md` exists at the root, the repository has multiple contexts. The map points to where each context lives:

```text
/
├── CONTEXT-MAP.md
├── docs/
│   └── adr/                          # system-wide decisions
├── src/
│   ├── ordering/
│   │   ├── CONTEXT.md
│   │   └── docs/adr/                 # context-specific decisions
│   └── billing/
│       ├── CONTEXT.md
│       └── docs/adr/
```

Create files lazily, only when there is something useful to write. If no `CONTEXT.md` exists, create one when the first term is resolved. If no `docs/adr/` directory exists, create it when the first ADR is needed.

## During the session

### Challenge against the glossary

When the user uses a term that conflicts with the existing language in `CONTEXT.md`, call it out immediately.

Example: "Your glossary defines 'cancellation' as X, but you seem to mean Y. Which is it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term.

Example: "You're saying 'account'. Do you mean the Customer or the User? Those are different concepts."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force the user to be precise about boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it.

Example: "Your code cancels entire Orders, but you just said partial cancellation is possible. Which is correct?"

### Update CONTEXT.md inline

When a term is resolved, update `CONTEXT.md` immediately. Do not batch updates until the end of the session. Use the format in [CONTEXT-FORMAT.md](CONTEXT-FORMAT.md).

Do not couple `CONTEXT.md` to implementation details. Only include terms that are meaningful to domain experts.

### Offer ADRs sparingly

Only offer to create an ADR when all three criteria are true:

1. **Hard to reverse**: the cost of changing the decision later is meaningful.
2. **Surprising without context**: a future reader will wonder why the decision was made.
3. **Result of a real trade-off**: there were genuine alternatives and one was chosen for specific reasons.

If any criterion is missing, skip the ADR. Use the format in [ADR-FORMAT.md](ADR-FORMAT.md).
