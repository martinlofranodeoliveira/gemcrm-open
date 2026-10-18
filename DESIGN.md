---
name: GemCRM Open
description: Practical Portuguese CRM interface for contacts, opportunities and next actions.
colors:
  ink: "#18323a"
  muted: "#53646b"
  paper: "#f6f8f7"
  line: "#dce4e2"
  surface: "#ffffff"
  accent: "#086957"
  accent-hover: "#055243"
  navigation: "#142e35"
  navigation-text: "#b9cecf"
  navigation-active: "#2c4c52"
  danger: "#a32e37"
  input-border: "#aabcb7"
  focus: "#168bce"
  pipeline: "#edf1ef"
  success-background: "#e0f0e7"
  success-text: "#245541"
typography:
  headline:
    fontFamily: 'Inter, "Segoe UI", system-ui, sans-serif'
    fontSize: "1.9rem"
    fontWeight: 650
    lineHeight: 1.2
    letterSpacing: "-0.03em"
  title:
    fontFamily: 'Inter, "Segoe UI", system-ui, sans-serif'
    fontSize: "1.12rem"
    fontWeight: 650
    lineHeight: 1.4
  body:
    fontFamily: 'Inter, "Segoe UI", system-ui, sans-serif'
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: 'Inter, "Segoe UI", system-ui, sans-serif'
    fontSize: "0.88rem"
    fontWeight: 600
rounded:
  surface: "12px"
  pipeline: "10px"
  item: "8px"
  button: "7px"
  control: "6px"
spacing:
  compact: "8px"
  control-gap: "12px"
  item: "16px"
  mobile-gutter: "20px"
  section: "24px"
  panel: "28px"
  group: "32px"
  desktop-gutter: "40px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.surface}"
    typography: "{typography.label}"
    rounded: "{rounded.button}"
    padding: "9px 16px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
    textColor: "{colors.surface}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.button}"
    padding: "9px 16px"
  button-danger:
    backgroundColor: "{colors.danger}"
    textColor: "{colors.surface}"
    rounded: "{rounded.button}"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "9px 12px"
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.surface}"
    padding: "28px"
---

# Design System: GemCRM Open

## Overview

This document records the implemented interface in `static/crm/app.css` and the
server-rendered templates. It is an extracted baseline, not a record of a user
selecting a visual metaphor or an approved image composition.

The current interface is a practical Portuguese workspace: restrained white and
pale green surfaces, dark teal navigation and an emerald action color. Its
visual structure supports reading records, editing forms and choosing the next
action. The interface uses text, semantic tables, native fields and small SVG
geometry; it does not depend on photography or illustrations.

**Key Characteristics:**

- One sans-serif family stack for labels, records and headings.
- Flat surfaces separated by borders, spacing and tonal changes.
- Familiar navigation, tables, forms and an explicitly operated pipeline.
- Structural changes at smaller widths, with readable content and visible focus.

## Colors

The palette combines a muted green-tinted workspace with strong, limited action
and navigation colors. The frontmatter records the extracted reusable values.

### Primary

- **Emerald action** (`accent`): primary buttons, text links, checkbox accent and
  text caret. `accent-hover` darkens primary buttons on hover.

### Neutral

- **Deep teal navigation** (`navigation`): the persistent desktop sidebar and
  mobile navigation band. Navigation text and active backgrounds use their own
  related tones.
- **Dark ink** (`ink`): headings, records, field values and primary body text.
- **Muted ink** (`muted`): explanations, dates, secondary labels and table heads.
- **Pale paper** (`paper`): workspace background.
- **White surface** (`surface`): records, tables, forms and the workspace header.
- **Fine divider** (`line`): panel outlines and row separators.
- **Pipeline surface** (`pipeline`): the stage columns behind opportunity items.

Destructive actions use `danger`; saved-record messages use the success pair.
The blue `focus` token distinguishes keyboard focus from selection and status.

## Typography

All roles use the same declared stack: Inter, Segoe UI, system UI, sans-serif.
There is no bundled font asset or remote font request in the current base
template; installed fonts determine the available face.

The desktop heading role is recorded above. Page headings reduce to (1.6rem) at
the medium breakpoint and (1.55rem) on mobile. Section headings use the title
role; record links use weight (600). Buttons and field labels share compact,
semibold treatment. Tables use (0.88rem) text, with smaller secondary metadata.

Heading explanations are constrained to (65ch). Financial values use tabular
numerals. Preserve ordinary mixed-case labels and Portuguese interface copy.

## Layout

The desktop workspace is a two-column grid: a sidebar (220px) beside a content
column that can shrink. The sidebar stays at the top of the viewport and fills
its height. The header is (68px) tall. Main content has a maximum width (1680px)
and horizontal gutters from the desktop-gutter spacing token.

At (1100px) and below, the sidebar narrows to (184px), main gutters become
(26px), and the dashboard switches from two content columns to one. At (700px)
and below, the sidebar becomes a normal document-flow navigation band. Its
links scroll horizontally. The header reduces to (46px), and the content uses
the mobile gutter token. Summary values become a two-column grid.

Tables remain tables inside horizontal overflow containers, with a minimum
table width (680px) on mobile. The five-stage pipeline scrolls horizontally;
mobile columns are (240px) wide. Record forms stay within (760px), confirmation
panels within (680px), and the authentication wrapper within (520px).

## Elevation & Depth

The current interface uses no shadows. Depth comes from the dark navigation
band, pale workspace, white content surfaces, one-pixel borders and row
dividers. Hover states change a surface or text color without moving content.

## Shapes

Containers have gently rounded corners, with smaller radii for buttons and
fields. The reusable radius values appear in the frontmatter. Border strokes
are thin and quiet. Keep form fields recognizable as native text, date, select
and checkbox controls; the task completion action is a labeled submit button.

## Components

### Buttons

Primary actions use emerald with white text; secondary actions use white with a
subtle outline and dark text. Destructive confirmation uses the danger color.
Buttons have a minimum height (42px). Their background and text transitions
last (150ms); reduced-motion preferences disable transitions.

Keyboard focus uses an outline (3px) with an offset (3px). Disabled buttons
reduce opacity to (0.6) and use a waiting cursor. Inline actions retain text-link
affordances rather than adopting the primary button treatment.

### Containers and tables

Content panels and tables use white surfaces and fine borders. Section headings
and record rows are separated with dividers. Tables have semantic column
headers, left-aligned text and a subtle row hover surface. Record names are
semibold links; destructive links use the danger color.

### Inputs and fields

Inputs, selects and textareas use white surfaces, the input-border token and a
minimum height (42px). Labels precede controls; required fields show an asterisk.
Help and validation messages follow the field and remain associated with it.
Error text uses a dark red treatment; non-field errors have a pale red surface.
Checkboxes use the native control with the emerald accent.

### Navigation

The desktop sidebar uses a brand link, a vertical set of navigation links and
account actions near the bottom. The current destination has a lighter teal
surface and white text; hover uses a related darker surface. Mobile preserves
the link vocabulary in a horizontal scrolling row.

### Opportunity pipeline and tasks

Opportunity stages are labeled columns with counts. White opportunity items
contain the title, company, value, optional closing date and an explicitly
submitted stage selector. No drag gesture is required.

Task rows use an explicitly named complete or reopen action, linked title, date
and visible status. Completed items add a filled check treatment and struck
record title. Stage badges and status text accompany color differences.

## Do's and Don'ts

### Do:

- **Do** reuse the shared color roles, field controls and action vocabulary.
- **Do** preserve visible keyboard focus, associated form labels and semantic
  tables when adding workflows.
- **Do** change layout structure at the observed breakpoints instead of scaling
  the entire interface down.
- **Do** use whitespace, dividers and tonal surfaces for grouping.

### Don't:

- **Don't** introduce a second display typeface for labels or data.
- **Don't** replace familiar fields with decorative custom controls.
- **Don't** add shadows, imagery or decorative motion as implied existing
  conventions; the current implementation establishes none.
- **Don't** rely on status color alone when text or a named action is available.
