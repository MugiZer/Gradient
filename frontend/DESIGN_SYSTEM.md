# Gradient Electron companion design system

Source of truth: ../DESIGN.md. The real Codex / IDE / harness is the primary surface; this renderer never owns the transcript, composer, editor, or file tree.

ENERGY 1 / RHYTHM 1 / MOTION 2. Gradient is one peripheral object, with no sidebar, dashboard, pipeline graph, permanent agent tabs, or mock coding workspace.

## Tokens and purpose

All visual tokens live in `src/styles/tokens.css`; motion definitions live in `src/motion/`.

| Element | Values | Reason |
| --- | --- | --- |
| Background and surfaces | #0d0d0d, #151515, #1b1b1b | Keep the coding surface quiet and establish shallow depth. |
| Text | #f4f4f4, #a6a6a6, #909090 | Distinguish content, secondary copy, and metadata while preserving normal-text contrast. The original #707070 was raised for readability. |
| Accent | #c8ddbb | Reserve a soft green for active connection, focus, progress, and verified success. |
| Character bodies | neutral #666964, sage #5c7664, clay #846c58 | Make the three roles distinct at 32 px without names or saturated decoration. |
| Typography | system sans for controls, Cascadia Code / SFMono-Regular / Consolas for code/evidence | Preserve familiar desktop controls and readable technical evidence without font downloads. |
| Spacing | 4, 8, 12, 16, 24 px | Use one spacing scale for compact surfaces. |
| Radii | 8, 12, 16 px | Distinguish controls, lesson surfaces, and expanded inspection surfaces. |
| Borders | white at 9% opacity | Define surfaces without a panel-heavy appearance. |
| Anchor | 32 px, 20 px from the bottom and right | Keep idle Gradient almost invisible. Mobile hit area is 44 px; the sprite stays 32 px. |
| Lesson / peek | 320 / 280 px | Limit secondary work to a small, readable surface. |
| Proof | 42dvh desktop; 65dvh on narrow screens | Give evidence temporary emphasis; stack results when two columns become unreadable. |

Only opened lesson surfaces use a shallow shadow. There are no decorative grids, gradients, hero illustrations, or background animation. The sparkle in lesson copy is the exact DESIGN.md affordance, not a general-purpose icon style.

## Sprites

`AgentSprite` owns the inline SVG for `gradient`, `observer`, and `builder`. The root is an asymmetric rounded body, the Observer a softened six-sided silhouette, and the Builder a rounded rectangle. Each uses a body path, two bright rounded eyes, and only an optional check or attention dot.

One SVG persists through idle, noticing, thinking, working, done, and attention. Idle may blink. Noticing shifts the eyes and briefly lifts the body. Thinking moves the eyes and gently pulses. Working moves the body slightly. Done settles with a check. Attention lifts with a dot. No raster characters or copied branded silhouettes are used.

## Motion and accessibility

`springSoft`: stiffness 420, damping 32, mass .8. `springSpawn`: stiffness 520, damping 28, mass .7. Micro durations are 180–260 ms; larger transitions use up to 360 ms. A 45 ms stagger separates the two agents. Spawn offsets are centralized and match the anchor's center at desktop and mobile sizes.

`LayoutGroup`, the `gradient-surface` layout ID, and `AnimatePresence` connect the root, tray, and artifacts. Exits reverse toward the same corner. Transform and opacity carry the motion. Gradient never renders or animates the host coding workspace.

`MotionConfig reducedMotion="user"`, `useReducedMotion`, and the CSS media query stop movement and blinking when reduced motion is requested. Native buttons, textarea, details, progress, and dialog provide platform semantics. Focus outlines remain visible. Escape dismisses the lesson or closes the peek/proof; native modal focus containment applies to proof. The anchor collapses/reopens expanded lesson surfaces without discarding their stage or evidence.

## Inspection

Build the renderer and run the Electron app. Use Electron **Demo** mode for staged UI inspection and **Live** mode for a real connected host task.

There is no browser showcase route. A browser load may only report that the renderer is Electron-only; it must never recreate a coding workspace.

Screenshots and recorded control checks are listed in `VERIFICATION.md`.
