---
version: alpha
name: dark-calendar-app-design
summary: "A focused dark-mode design system for a calendar and scheduling app. It combines a near-black canvas, charcoal panels, restrained lavender-blue primary actions, clear time-grid hierarchy, and status colors for event types and task states."

colors:
  primary: "#5e6ad2"
  on-primary: "#ffffff"
  primary-hover: "#828fff"
  primary-focus: "#5e69d1"
  canvas: "#010102"
  surface-1: "#0f1011"
  surface-2: "#141516"
  surface-3: "#18191a"
  surface-raised: "#202124"
  ink: "#f7f8f8"
  ink-muted: "#d0d6e0"
  ink-subtle: "#8a8f98"
  ink-disabled: "#8a8f98"
  hairline: "#23252a"
  hairline-strong: "#34343a"
  today-bg: "#15172a"
  selected-bg: "#1d2144"
  busy: "#5e6ad2"
  tentative: "#7a7fad"
  personal: "#27a644"
  focus-time: "#2f80ed"
  deadline: "#f2994a"
  conflict: "#eb5757"
  overlay: "#000000"
typography:
  display-xl:
    fontFamily: "Product Display, SF Pro Display, -apple-system, system-ui, sans-serif"
    fontSize: 64px
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: -2.2px
  display-lg:
    fontFamily: "Product Display, SF Pro Display, -apple-system, system-ui, sans-serif"
    fontSize: 44px
    fontWeight: 600
    lineHeight: 1.12
    letterSpacing: -1.2px
  headline:
    fontFamily: "Product Display, SF Pro Display, -apple-system, system-ui, sans-serif"
    fontSize: 28px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: -0.6px
  title:
    fontFamily: "Product Text, Inter, -apple-system, system-ui, sans-serif"
    fontSize: 20px
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: -0.2px
  body:
    fontFamily: "Product Text, Inter, -apple-system, system-ui, sans-serif"
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: -0.05px
  body-sm:
    fontFamily: "Product Text, Inter, -apple-system, system-ui, sans-serif"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.45
    letterSpacing: 0
  caption:
    fontFamily: "Product Text, Inter, -apple-system, system-ui, sans-serif"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.35
    letterSpacing: 0
  button:
    fontFamily: "Product Text, Inter, -apple-system, system-ui, sans-serif"
    fontSize: 14px
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: 0
  time-label:
    fontFamily: "Product Mono, ui-monospace, SF Mono, Menlo, monospace"
    fontSize: 12px
    fontWeight: 400
    lineHeight: 1.2
    letterSpacing: 0
rounded:
  xs: 4px
  sm: 6px
  md: 8px
  lg: 12px
  xl: 16px
  pill: 9999px
  full: 9999px
spacing:
  xxs: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
  section: 80px

components:
  app-shell:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
  top-bar:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    height: 56px
  sidebar:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink-muted}"
    typography: "{typography.body-sm}"
    width: 280px
  month-mini-calendar:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink-muted}"
    typography: "{typography.caption}"
    rounded: "{rounded.lg}"
    padding: 12px
  calendar-grid:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
  day-column:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
  today-column:
    backgroundColor: "{colors.today-bg}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
  time-ruler:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink-subtle}"
    typography: "{typography.time-label}"
    width: 64px
  current-time-line:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.caption}"
    height: 2px
  event-card:
    backgroundColor: "{colors.busy}"
    textColor: "{colors.on-primary}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: 6px 8px
  event-card-tentative:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.ink-muted}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: 6px 8px
  event-card-personal:
    backgroundColor: "{colors.personal}"
    textColor: "#111111"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: 6px 8px
  focus-ring:
    backgroundColor: "{colors.primary-focus}"
    textColor: "{colors.on-primary}"
    typography: "{typography.caption}"
    height: 2px
  grid-line:
    backgroundColor: "{colors.hairline}"
    textColor: "{colors.ink}"
    typography: "{typography.caption}"
    height: 1px
  strong-grid-line:
    backgroundColor: "{colors.hairline-strong}"
    textColor: "{colors.ink}"
    typography: "{typography.caption}"
    height: 1px
  tentative-dot:
    backgroundColor: "{colors.tentative}"
    textColor: "#101010"
    typography: "{typography.caption}"
    rounded: "{rounded.full}"
    size: 8px
  focus-block:
    backgroundColor: "{colors.focus-time}"
    textColor: "#101010"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: 6px 8px
  button-disabled:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink-disabled}"
    typography: "{typography.button}"
    rounded: "{rounded.md}"
    padding: 8px 14px
  overlay-scrim:
    backgroundColor: "{colors.overlay}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
  event-card-deadline:
    backgroundColor: "{colors.deadline}"
    textColor: "#111111"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: 6px 8px
  conflict-badge:
    backgroundColor: "{colors.conflict}"
    textColor: "#111111"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
    padding: 2px 8px
  task-card:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: 12px
  task-card-selected:
    backgroundColor: "{colors.selected-bg}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: 12px
  inspector-panel:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    width: 360px
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button}"
    rounded: "{rounded.md}"
    padding: 8px 14px
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "#101010"
    typography: "{typography.button}"
    rounded: "{rounded.md}"
    padding: 8px 14px
  button-secondary:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink}"
    typography: "{typography.button}"
    rounded: "{rounded.md}"
    padding: 8px 14px
  segmented-control:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink-subtle}"
    typography: "{typography.button}"
    rounded: "{rounded.pill}"
    padding: 4px
  segmented-control-selected:
    backgroundColor: "{colors.surface-3}"
    textColor: "{colors.ink}"
    typography: "{typography.button}"
    rounded: "{rounded.pill}"
    padding: 6px 12px
  text-input:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: 8px 12px
  modal:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.xl}"
    padding: 24px
  toast:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: 12px 16px
---

# Calendar App Design System

## Overview

This design system is optimized for a calendar app where the primary work surface is a time grid. The UI should feel calm, precise, and highly readable during schedule planning. The canvas stays near-black, panels sit one or two levels above it, and color is used only to clarify intent: primary actions, today, selected time ranges, event categories, deadlines, and conflicts.

The calendar is not a marketing page. Product screenshots, decorative hero sections, and large brand moments are not core patterns. The main experience is an application shell with a persistent top bar, sidebar navigation, calendar grid, and optional inspector panel for event or task details.

## Product Principles

- **Time is the primary layout primitive.** Align visual rhythm to hours, days, weeks, and months.
- **Hierarchy must not fight the grid.** Use borders, muted text, and subtle surface changes before using strong color.
- **Color communicates state.** Lavender marks the primary action and busy/default events; warm colors are reserved for deadlines or conflicts.
- **Editing should feel direct.** Dragging, resizing, and selecting time blocks must expose clear focus and hover states.
- **Density is acceptable, clutter is not.** Support many events while keeping labels, time ranges, and overlap readable.

## Colors

### Core Surfaces

- `{colors.canvas}`: app background and default calendar grid.
- `{colors.surface-1}`: sidebar, task cards, popovers, low-emphasis panels.
- `{colors.surface-2}`: modals, elevated inspector sections, selected overlay surfaces.
- `{colors.surface-3}`: selected segment controls and nested raised areas.
- `{colors.hairline}`: grid lines, dividers, and panel borders.
- `{colors.hairline-strong}`: input borders, focus-adjacent dividers, and stronger outlines.

### Calendar State Colors

- `{colors.today-bg}`: today's column or date cell background.
- `{colors.selected-bg}`: selected time range, selected task, or active detail row.
- `{colors.busy}`: default scheduled event.
- `{colors.tentative}`: tentative event outline or secondary state.
- `{colors.personal}`: personal calendar event.
- `{colors.focus-time}`: reserved focus block.
- `{colors.deadline}`: due date and deadline reminders.
- `{colors.conflict}`: overlapping event warning or scheduling conflict.

## Typography

Use compact, readable typography. Calendar UIs contain repeated labels, so avoid excessive font weight.

- Display styles are reserved for empty states, onboarding, or page-level introductions.
- `{typography.headline}` and `{typography.title}` are used for panel headers and event detail headings.
- `{typography.body}` is used for forms and readable descriptions.
- `{typography.body-sm}` is the default calendar event and sidebar text size.
- `{typography.caption}` is used for metadata, participants, location, and helper text.
- `{typography.time-label}` is used for the time ruler to keep hour labels stable and scannable.

## Layout

### App Shell

Desktop layout uses three zones:

1. **Sidebar**: mini month calendar, calendar list, filters, and task backlog.
2. **Main calendar**: day, week, work-week, month, or agenda view.
3. **Inspector panel**: selected event, task, or scheduling assistant detail.

The inspector may be hidden by default on narrower screens and opened as a drawer.

### Calendar Grid

- Time ruler width: 64px.
- Hour row height: 56–72px depending on density setting.
- Day columns use 1px hairline dividers.
- Current time line uses a 2px primary line with a small circular marker at the day column edge.
- Today uses a subtle tinted background, not a saturated full-column fill.
- Selected ranges should be visible behind events without reducing event readability.

### Month View

- Month cells keep a minimum height of 112px on desktop.
- Date number sits top-left; today's date uses a primary pill or tinted circle.
- More-than-visible events collapse into a `+N more` row.
- Weekends may use slightly lower contrast, but must remain readable.

## Components

### Navigation

- `top-bar`: contains app title, search, view switcher, date navigation, and primary create button.
- `sidebar`: contains mini calendar, calendars, filters, and task backlog.
- `segmented-control`: switches between Day, Week, Month, and Agenda views.

### Calendar

- `calendar-grid`: root grid surface for day/week views.
- `time-ruler`: sticky time labels on the left edge.
- `day-column`: default day column.
- `today-column`: highlighted day column for the current date.
- `current-time-line`: real-time indicator across the current day.
- `event-card`: default scheduled event.
- `event-card-tentative`: tentative event with outlined emphasis.
- `event-card-personal`: personal event category.
- `event-card-deadline`: deadline or due-date event.
- `conflict-badge`: warning chip for overlapping or impossible schedules.

### Tasks and Scheduling

- `task-card`: unscheduled or planned work item.
- `task-card-selected`: selected task ready for scheduling or editing.
- Task cards should expose duration, priority, deadline, and whether they are already scheduled.
- Dragging a task onto the calendar should preview the destination time block using `{colors.selected-bg}`.

### Forms and Feedback

- `text-input`: event title, location, attendee, and note fields.
- `modal`: create/edit event flow on desktop and tablet.
- `toast`: save confirmation, sync state, and undo affordance.

## Interaction States

- **Hover**: lift event cards one surface level or increase border contrast.
- **Focus**: use a 2px `{colors.primary-focus}` outline with visible offset.
- **Selected**: apply `{colors.selected-bg}` plus a primary outline when precision matters.
- **Dragging**: show a semi-transparent event preview and snap to the active time increment.
- **Conflict**: show `{colors.conflict}` only when overlap requires user attention.
- **Disabled**: use `{colors.ink-disabled}` and do not rely on opacity alone.

## Responsive Behavior

| Width | Behavior |
| --- | --- |
| ≥1280px | Full shell: sidebar, main calendar, optional inspector. |
| 1024–1279px | Sidebar can collapse; inspector opens as drawer. |
| 768–1023px | Week view reduces metadata; day and agenda views become primary. |
| <768px | Bottom navigation, single-day agenda, create/edit as full-screen sheet. |
| <480px | Month view becomes agenda-first; dense grids are avoided. |

Touch targets must be at least 44px high on mobile. Drag handles need visible affordances on touch devices, not hover-only behavior.

## Accessibility

- Maintain WCAG AA contrast for event text and essential labels.
- Do not communicate event category by color alone; include labels, icons, or calendar names.
- Keyboard users must be able to move by day, week, and time increment.
- Screen readers need event title, time range, calendar name, location, and conflict state.
- The current time line should not trap focus.

## Do's and Don'ts

### Do

- Use the grid as the main visual structure.
- Keep event cards compact and legible.
- Reserve strong colors for state and category.
- Make today, current time, and selected ranges immediately identifiable.
- Provide clear empty states for days without events and tasks without schedules.

### Don't

- Do not use decorative gradients or spotlight cards in the app shell.
- Do not make every calendar category equally saturated.
- Do not hide conflict information behind hover-only interactions.
- Do not rely on screenshots or marketing layouts as primary app components.
- Do not overuse pill shapes; use them for badges, toggles, and date markers.

## Implementation Notes

1. Build the app shell first: `top-bar`, `sidebar`, and `calendar-grid`.
2. Implement day/week views before month view because they define drag, resize, conflict, and current-time behavior.
3. Treat `event-card` as the canonical event component and add category variants only when needed.
4. Keep scheduling task behavior in `task-card` and `task-card-selected` so backlog-to-calendar flows stay consistent.
5. Validate color contrast for each event category before shipping.
