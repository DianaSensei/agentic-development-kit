---
name: ui-ux-design-skill
description: In-depth UI/UX design knowledge - usability, accessibility, and consistency principles, and responsive/cross-platform design for desktop apps. Use when a feature has a UI component that needs design before implementation; coordinates with `tauri-react-skill` for the actual build.
metadata:
  domain: design
  triggers: UI, UX, usability, accessibility, a11y, WCAG, responsive design, cross-platform layout, interaction design, information hierarchy, design consistency, user flow
  role: specialist
  scope: design
  output-format: document
  related-skills: tauri-react-skill, feature-development, api-contract-skill, code-review-skill
---

# UI/UX Design

## Discover
Read the existing design system, if any: design tokens (color, spacing, typography), the component library in use, the style guide in `CLAUDE.md` or a dedicated convention file. Stay consistent - don't invent a new UI pattern when a standard already exists.

## Usability Heuristics (Nielsen, applied practically)
- **Visibility of system status**: always tell the user what's happening (loading, progress, saved or not) - never let the UI go silent while something is processing.
- **Error prevention & recovery**: validate before submit where possible, show a clear error message with how to fix it, not just a generic "Error."
- **Consistency**: the same action must work the same way everywhere in the app (don't use a button in one place and a gesture in another for the same function).
- **User control**: always provide a way back (Cancel/Undo) for an action that isn't immediately irreversible, where feasible.

## Accessibility (a11y)
- Sufficient color contrast (WCAG AA minimum: 4.5:1 for normal text).
- Full keyboard navigation support (Tab/Enter/Esc) - matters even more for a desktop app than mobile, since desktop users are accustomed to keyboard-driven interaction.
- Clear labels for inputs/buttons (not just an icon with no text/aria-label).
- Touch/click targets large enough (minimum ~44x44px) even on desktop, since a touch-capable screen (a Windows tablet) may still run the app.

## Responsive & Cross-Platform (desktop-app-specific)
- Test the layout at multiple window sizes (the user can resize freely, unlike a fixed mobile app) - avoid a layout that breaks when the window shrinks.
- Respect each OS's own UI conventions where it makes sense (macOS menu bar at the top of the screen vs. inside the window on Windows/Linux) - while still keeping the core experience consistent.
- Dark mode/light mode: if supported, ensure every color uses a token instead of a hardcoded value, to avoid a few spots that don't follow the theme.

## Information Architecture
Before designing a specific screen, clarify: what information the user needs to see first (display priority), and the main interaction flow (how many steps to complete the primary task - fewer is better, but not at the cost of clarity).

## When Multiple Reasonable Design Directions Exist
For a small screen/flow with a clear scope (adding one form, one list, one dialog, etc.) - choose the best option per the usability heuristics above (favor familiarity/consistency with the app's existing patterns over novelty), stating the reasoning briefly instead of asking first. Only present 2-3 options with trade-offs (simpler vs. more flexible, familiar vs. novel) and let the user choose when it's a LARGE screen/flow that affects many other parts of the app or changes a mental model users are already used to - a decision that's hard to reverse once users have adapted to it.

## Boundaries
This skill designs the IDEA/layout/UX flow - implementing the actual code (a React component, a Tauri command) belongs to `tauri-react-skill`. If a visual mockup is needed, a temporary HTML/React artifact can be created to help the user visualize it before real code is written.

What this skill does NOT own is **visual direction**: type scale, colour palette, spacing rhythm, shadow/elevation language, motion. The heuristics above tell you whether a screen is usable, not whether it looks considered - those are different questions, and this skill deliberately answers only the first.

If a design-taste skill is present in the session (`design-taste-frontend`, `minimalist-ui`, `high-end-visual-design`, `industrial-brutalist-ui`, or a similar house-style skill), read it for that visual layer and apply it on top of the usability/accessibility constraints here - the constraints win where the two conflict, because a design that fails WCAG AA contrast is not saved by being beautiful. If no such skill is present, stay with the project's existing design tokens and component library found in Discover, and do not invent a new visual language.

This is a soft reference on purpose. None of those skills ship with this plugin and none is declared as a dependency, so this section is a no-op when they are absent - see the companion-plugin note in the root [`README.md`](../../README.md) for how to install them separately.

## Knowledge Reference

Nielsen's usability heuristics, WCAG accessibility contrast/keyboard-navigation requirements, design tokens, responsive layout at variable window sizes, per-OS UI conventions, dark/light theming, information architecture.
