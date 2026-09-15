# Gradient Frontend Design Specification

59. DESIGN PHILOSOPHY — LOCKED


Gradient should feel calm, expressive, and intentional — never like a generic AI dashboard.

• Objects, not dashboards. Show meaningful things directly: agents, lessons, environments, proofs.
• Hierarchy before completeness. The important meaning should be obvious before technical detail.
• Progressive disclosure. Reveal deeper information only when the user investigates.
• Semantic zoom. Going deeper should change the representation, not just add more text.
• Structured information over prose. Prefer spatial / grouped representations when the information has structure.
• Direct manipulation. Let users interact with the object itself instead of surrounding it with generic controls.
• State through the object. Use sprite posture, eyes, subtle bounce, pulse, glow, or quiet surface changes instead of persistent status chrome.
• Low interaction cost. Minimize reading, scrolling, remembering, navigation, and unnecessary decisions.
• Visual restraint. Prefer typography, spacing, alignment, and subtle hairlines over nested cards, gradients, large shadows, or decorative “AI” effects.
• Design around the user’s mental model, not the backend schema.

Micro-motion is welcome when it adds personality or communicates state. Keep it subtle, fast, and localized.

Canonical rule:

“Show the meaning first. Let the implementation appear only when the user asks for it.”


60. DEFAULT CODEX EXPERIENCE


The screen should still feel like Codex.


Example:


┌─────────────────────────────────────────────────────────────┐
│ CODEX                                                       │
│                                                             │
│ > Add a regression test proving another process can read... │
│                                                             │
│ Codex                                                       │
│ [edits repo / runs tests]                                   │
│                                                             │
│ ❯                                                           │
│                                                             │
│                                                     ●●      │
│                                                  Gradient   │
└─────────────────────────────────────────────────────────────┘


No permanent agent dashboard.
No permanent pipeline graph.
No giant status board.


61. CORRECTION DETECTION UX


When Gradient detects a likely teachable correction, it should not hijack the workflow.


The small sprite subtly reacts:
• eyes shift,
• slight bounce,
• tiny glow or pulse.


Then surface a compact affordance:


“Possible lesson”


or:


“Lesson found”


Clicking the Gradient control opens a tiny panel such as:


Gradient


✦ I noticed a correction


Observable Effect
vs Simulation


[ Teach lesson ]


Do not lead with internal language such as:
• LearningEvent,
• confidence 0.94,
• capability extraction,
• reward model,
• TaskSpec.


Those belong in expandable technical details.


User-facing language should center on:
“Teach lesson.”


62. USER CONFIRMATION BEFORE POST-TRAINING PIPELINE


Ambient detection remains automatic.


However, the expensive / consequential lesson-generation pipeline should begin only after the user explicitly clicks:


[ Teach lesson ]


This preserves:
• ambient observation,
• explicit user intent,
• privacy / consent clarity,
• better product feel,
• a strong demo interaction.


Canonical flow:


correction detected
→ subtle Gradient notification
→ user clicks Gradient
→ “Teach lesson”
→ Gradient deploys the learning agents.


63. AGENT SPAWN UX — LOCKED


Clicking “Teach lesson” should visually deploy the Gradient agents from the bottom-right control.


Before:


[ Gradient sprite ]


After:


[ Observer ]   [ Environment Builder ]


Do not show the Codex Worker as a separate Gradient tab.
Codex is already visibly present as the active Worker Agent.


The three-agent system is therefore:


1. Codex Worker — visible in the main coding surface.
2. Gradient Observer — spawned in the small tray.
3. Gradient Environment Builder — spawned in the small tray.


The spawn animation should be subtle and fast, around 150–250 ms.


The visual effect should imply:
“Gradient just deployed agents because of my correction.”


Do not use a large orchestration graph.


64. AGENT STATUS HIERARCHY


Use progressive disclosure and semantic zoom.


Level 1 — AMBIENT

Presence and state only.

Example:
[ Observer ◌ ] [ Builder ○ ]


Level 2 — PREVIEW

Show what is happening or what was produced.

Observer:
“Understanding what you taught”

Environment Builder:
“Creating executable lessons”


Level 3 — EXPLORE

Reveal the meaningful structure of the artifact: capabilities, environments, evidence, or other objects the user can recognize and select.


Level 4 — INSPECT

Explain one selected object: what it means, why it exists, and what it is teaching or proving.


Level 5 — SPECIFICATION / EVIDENCE

Reveal raw implementation detail only on demand:
• TaskSpecs,
• verifier details,
• raw agent outputs,
• hashes,
• provenance,
• rollout traces.


Each level should answer a different user question. Deeper levels should not merely become longer versions of the previous one.

Technical detail should always be available, but never dominate the default experience.


65. AGENT LIFECYCLE STATES


The avatar itself should communicate state when possible.


Recommended states:


IDLE
• still,
• occasional blink.


THINKING
• subtle eye motion,
• gentle body pulse.


WORKING
• small repeated motion,
• no spinner unless necessary.


DONE
• settles,
• tiny check or quiet completion state.


NEEDS ATTENTION
• small lift / attention indicator.


Do not make the user read a secondary status system unless needed.


66. AGENTS SHOULD DISAPPEAR INTO ARTIFACTS


Do not accumulate permanent agent tabs.


Example lifecycle:


Stage 0:
[ Gradient ]


Stage 1:
[ Gradient ]  ✦ Lesson?


Stage 2:
[ Observer ◌ ] [ Builder ○ ]


Stage 3:
[ Observer ✓ ] [ Builder ◌ ]


Stage 4:
[ Lesson ✓ ]
8 train · 4 eval


Once an agent has completed its role, it should collapse into the resulting artifact.


This keeps the system calm and avoids an “agent graveyard.”


67. TRAINING IS NOT AN AGENT


Do not create a cute “Trainer Agent.”


Training is infrastructure, not an autonomous reasoning role.


After the Environment Builder finishes, replace the agent tray with a compact artifact card:


✦ Lesson ready


8 training · 4 frozen eval


[ Post-train agent ]


If the user starts training:


Post-training Qwen
████████████░░░


Prime may be visible in technical details, but not anthropomorphized as an agent.


Canonical semantic distinction:


Agents reason.
Training infrastructure executes.


68. POST-TRAINING COMPLETION STATE


After training completes, the small Gradient control should become:


✦ Lesson learned


Observable Effect
vs Simulation


Base        Gradient
1/5         5/5


[ Run proof ]


The user remains in the Codex workflow.


Gradient never becomes a destination they have to navigate to.


69. PROOF OVERLAY


“Run proof” is the one moment when Gradient is allowed to occupy a larger part of the screen.


Use a temporary overlay or expandable bottom panel.


Canonical layout:


┌────────────────────────────────────────────────────────────┐
│ UNSEEN TASK                                                │
│ frozen before training                                     │
│                                                            │
│  BASE QWEN                    GRADIENT QWEN                 │
│                                                            │
│  simulated result             real effect observed         │
│                                                            │
│       FAIL                        PASS                      │
│                                                            │
│ Same model · Same task · Same verifier · Different weights │
└────────────────────────────────────────────────────────────┘


Then close the overlay and return immediately to Codex.


This preserves the ambient product philosophy while giving the result enough visual weight.


70. NO ORCHESTRATION BOARD


Do not show permanent arrows or a pipeline diagram in the default UI.


The backend architecture is:


Observer → Environment Agent → compiler → training → eval


But the user should not be forced to manage or monitor that graph.


Default UX:
• Observer finishes,
• Builder starts,
• lesson becomes ready.


The system coordinates itself.


The user is only brought back for meaningful decisions:
• Teach lesson,
• Post-train agent,
• Run proof.


71. UI IMPLEMENTATION STRATEGY


Do not try to inject a graphical widget into the stock terminal interface.


Use the real Codex runtime / app-server as the backend and build a very thin custom client.


Architecture:


codex app-server
        │
        ├── Codex conversation/events
        └── Gradient agent state
                │
                ▼
         Gradient Client UI


The client should visually feel like a minimal Codex developer console:
• dark background,
• monospace conversation,
• compact tool actions,
• diff summaries,
• message composer,
• tiny Gradient control in the bottom-right.


Use the real backend event stream and keep the client thin and purpose-built.

The UI is a client over the real Codex runtime, not a fake imitation of agent behavior.


72. FINAL UI PRODUCT PRINCIPLE


The final product should feel like:


“You are using Codex normally.
Gradient notices when you teach it something.
You click Teach lesson.
Small agents quietly appear, do the work, then disappear into a learned capability.”


Canonical product line:


“You never really go to Gradient.
Gradient comes alive inside the place where you are already teaching an agent.”


This is the strongest UI expression of the Agents Everywhere theme for Gradient


73. FRONTEND IMPLEMENTATION SPEC — LOCKED


This section supersedes the earlier preference for a vanilla HTML/JS frontend.


Because Gradient needs persistent interactive state, progressive disclosure, semantic zoom, transient overlays, expressive sprites, and a real backend event stream, the preferred frontend stack is:


• React
• Vite
• Motion (formerly Framer Motion)
• Radix primitives only where useful for accessibility / popovers / dialogs
• plain CSS + CSS variables for the design system
• Lucide only for utility icons
• custom inline SVG for Gradient characters


Avoid:
• Next.js,
• Redux,
• large component frameworks,
• Tailwind dependency sprawl,
• shadcn as the primary visual language,
• generic SaaS dashboard components.


The frontend should remain small and purpose-built.


74. EXACT COMPONENT TREE — LOCKED


Canonical React component hierarchy:


<App>
└── <CodexWorkspace>
    ├── <CodexTranscript>
    │   ├── <UserTurn />
    │   ├── <AgentTurn />
    │   ├── <ToolAction />
    │   └── <DiffPreview />
    │
    ├── <Composer />
    │
    └── <GradientLayer>
        ├── <GradientAnchor />
        │   └── <AgentSprite role="gradient" />
        │
        ├── <LessonNudge />
        │
        ├── <LessonPopover />
        │   ├── <LessonSummary />
        │   └── <TeachLessonButton />
        │
        ├── <AgentTray />
        │   ├── <AgentSprite role="observer" />
        │   └── <AgentSprite role="builder" />
        │
        ├── <AgentPeek />
        │
        ├── <LessonArtifact />
        │
        ├── <TrainingProgress />
        │
        ├── <LearnedArtifact />
        │
        ├── <ProofDrawer />
        │   ├── <BaseResult />
        │   ├── <TrainedResult />
        │   └── <ProofFooter />
        │
        └── <TechnicalDetails />


Astra should implement this structure directly rather than inventing a new frontend architecture.


75. COMPONENT CONTRACTS


A. GradientAnchor


Purpose:
Persistent ambient Gradient presence.


Default:
• 32×32 px,
• bottom: approximately 20 px,
• right: approximately 20 px,
• always visible,
• contains only the root Gradient sprite.


It must not look like a generic floating chatbot button.


B. AgentSprite


Canonical types:


type AgentRole =
  | "gradient"
  | "observer"
  | "builder"


type AgentState =
  | "idle"
  | "noticing"
  | "thinking"
  | "working"
  | "done"
  | "attention"


Canonical usage:


<AgentSprite
  role="observer"
  state="thinking"
  size={32}
/>


Every sprite should be custom inline SVG with:
• body path,
• left eye,
• right eye,
• optional tiny status glyph.


The same SVG object should transform between states.
Do not swap raster assets for each state.


C. LessonNudge


Exists only when:
state === "lesson_candidate"


Primary content:
“✦ Lesson found”


Position:
immediately adjacent to the Gradient anchor.


Do not use:
• top-of-screen toast,
• modal,
• large notification.


D. LessonPopover


Target width:
approximately 300–340 px.


Canonical contents:


✦ I noticed a correction


Observable Effect
vs Simulation


[ Teach lesson ]


Secondary action:
Dismiss


No extra controls.


E. AgentTray


The tray must grow spatially from GradientAnchor.


Collapsed:
[ Gradient ]


After Teach Lesson:
[ Observer ] [ Builder ]


Approximate geometry:
• height: 48–56 px,
• padding: ~8 px,
• gap: ~10 px.


Use Motion shared-layout techniques / layout IDs so the tray feels like the original ambient object transformed rather than a new panel appearing.


Do not show agent names unless hovered / clicked.


F. AgentPeek


Observer example:


Observer


Understanding what you taught


Observable Effect
vs Simulation


Builder example:


Environment Builder


Creating executable lessons


6 / 12 complete


Approximate width:
260–300 px.


G. LessonArtifact


When agent work is complete, the agents collapse into the resulting artifact:


✦ Lesson ready


Observable Effect vs Simulation


8 train · 4 unseen


[ Post-train agent ]


The Observer and Builder avatars disappear into this artifact state.


H. TrainingProgress


Training is infrastructure, not an agent.


Canonical display:


Post-training Qwen 2B


████████░░░


Prime run #...


Keep visually quiet.


I. LearnedArtifact


After training:


✦ Lesson learned


Observable Effect vs Simulation


Base       Gradient
1 / 5      5 / 5


[ Run proof ]


J. ProofDrawer


Temporary bottom drawer / overlay.


Target:
roughly 35–45% of viewport height.


Canonical layout:


UNSEEN TASK
Frozen before training


┌────────────────────┬────────────────────┐
│ BASE QWEN          │ GRADIENT QWEN      │
│                    │                    │
│ generated code     │ generated code     │
│                    │                    │
│ ❌ FAIL            │ ✅ PASS            │
└────────────────────┴────────────────────┘


Same model · Same task · Same verifier
Different weights


This is the only large Gradient surface.


76. FRONTEND FILE STRUCTURE — LOCKED


frontend/
├── src/
│   ├── App.tsx
│   │
│   ├── codex/
│   │   ├── CodexWorkspace.tsx
│   │   ├── CodexTranscript.tsx
│   │   ├── Composer.tsx
│   │   ├── ToolAction.tsx
│   │   └── DiffPreview.tsx
│   │
│   ├── gradient/
│   │   ├── GradientLayer.tsx
│   │   ├── GradientAnchor.tsx
│   │   ├── AgentSprite.tsx
│   │   ├── LessonNudge.tsx
│   │   ├── LessonPopover.tsx
│   │   ├── AgentTray.tsx
│   │   ├── AgentPeek.tsx
│   │   ├── LessonArtifact.tsx
│   │   ├── TrainingProgress.tsx
│   │   ├── LearnedArtifact.tsx
│   │   ├── ProofDrawer.tsx
│   │   └── TechnicalDetails.tsx
│   │
│   ├── state/
│   │   ├── gradientMachine.ts
│   │   └── useGradientEvents.ts
│   │
│   ├── motion/
│   │   ├── springs.ts
│   │   └── variants.ts
│   │
│   └── styles/
│       ├── tokens.css
│       ├── codex.css
│       └── gradient.css
│
└── public/


Also create:


frontend/
├── DESIGN_SYSTEM.md
└── INTERACTION_STATES.md


DESIGN_SYSTEM.md:
• design tokens,
• sprite rules,
• spacing,
• typography,
• surfaces,
• borders,
• motion principles.


INTERACTION_STATES.md:
• state machine,
• allowed transitions,
• event mapping,
• component visibility by state,
• animation expectations.


77. DESIGN TOKENS


Use centralized CSS variables rather than per-component invention.


Starting point:


:root {
  --bg: #0d0d0d;
  --surface-1: #151515;
  --surface-2: #1b1b1b;


  --text-1: #f4f4f4;
  --text-2: #a6a6a6;
  --text-3: #707070;


  --border: rgba(255,255,255,.09);


  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;


  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 24px;


  --agent-size: 32px;


  --motion-fast: 180ms;
  --motion-normal: 260ms;
  --motion-large: 360ms;
}


These values may be tuned during visual QA, but Astra must not invent independent spacing/radius/motion rules in every component.


78. MOTION TOKENS — LOCKED


Motion is restrained but expressive. Use it to communicate personality, lifecycle, attention, origin, or spatial continuity — never to decorate every transition.

Centralize spring definitions.


Starting point:


export const springSoft = {
  type: "spring",
  stiffness: 420,
  damping: 32,
  mass: 0.8,
}


export const springSpawn = {
  type: "spring",
  stiffness: 520,
  damping: 28,
  mass: 0.7,
}


Rules:
• most micro-transitions: ~160–260 ms,
• larger tray transitions: ~260–400 ms,
• primarily animate transform, opacity, SVG transforms,
• avoid layout-heavy animation,
• target 60 fps,
• avoid abrupt layout shifts,
• respect prefers-reduced-motion,
• do not define random motion constants inside individual components.


Critical spawn animation:


Before:
Gradient


After Teach Lesson:
Gradient → Observer + Environment Builder


The Observer and Builder must visually originate from the Gradient anchor using:
• scale,
• translation,
• opacity,
• slight stagger.


Total perceived transition:
under ~350 ms.


79. UI STATE MACHINE — LOCKED


Canonical frontend stages:


type GradientStage =
  | "idle"
  | "lesson_candidate"
  | "lesson_open"
  | "observer_working"
  | "builder_working"
  | "lesson_ready"
  | "training"
  | "learned"
  | "proof"


Primary transition path:


idle
↓
lesson_candidate
↓
lesson_open
↓ Teach lesson
observer_working
↓
builder_working
↓
lesson_ready
↓ Post-train
training
↓
learned
↓ Run proof
proof


Dismiss path:


lesson_candidate
→ idle


Astra should not invent additional top-level UI stages without a concrete backend requirement.


Do not manage this experience with a large collection of unrelated booleans such as:
• isObserverOpen,
• showBuilder,
• isAnimating,
• trainingDone,
• showLesson.


Use one explicit state machine.


80. BACKEND EVENT → UI STATE MAPPING


Canonical WebSocket mapping:


correction_candidate
→ lesson_candidate


lesson_confirmed
→ observer_working


capability_extracted
→ builder_working


curriculum_compiled
→ lesson_ready


training_started
→ training


training_completed
→ learned


proof_started
→ proof


Animations represent real backend state changes.


Do not use fake setTimeout-based demo timing to pretend agent work occurred.


81. DESIGN REFERENCE HANDLING


Store visual references separately, for example:


design_refs/
├── grok_agents_reference.png
└── additional_reference_screenshots/


Instruction to Astra:


Study the references for:
• avatar simplicity,
• tiny-scale legibility,
• shared visual grammar,
• expressive eyes,
• silhouette variation,
• state communicated through the object,
• progressive disclosure and semantic zoom,
• structured information instead of narrated prose,
• peripheral reassurance instead of constant supervision,
• removing controls / metadata that make the user manage the system,
• smooth, restrained motion.


Do not reproduce copyrighted character assets or exact silhouettes.


The goal is the interaction philosophy and visual clarity, not visual cloning.


82. UI STATE SHOWCASE — BUILD BEFORE LIVE WIRING


Before connecting the full backend event stream, create a developer-only route:


/dev/ui


It should allow manual traversal of every UI state:


[ idle ]
[ lesson_candidate ]
[ lesson_open ]
[ observer_working ]
[ builder_working ]
[ lesson_ready ]
[ training ]
[ learned ]
[ proof ]


Purpose:
• visually inspect every state,
• tune animation,
• test transitions,
• verify small-screen behavior,
• fix motion before debugging backend integration.


Only after the state showcase feels right should the frontend be wired to real WebSocket events.


83. VISUAL ACCEPTANCE CRITERIA — LOCKED


Astra should treat these as acceptance tests:


1. At 100% zoom, the user should see almost no Gradient UI while idle.
2. Gradient should occupy less than roughly 5% of the viewport until explicitly opened.
3. No persistent sidebar.
4. Before the user intentionally enters an Explore / Inspect state, no Gradient surface should exceed roughly 340 px. Larger temporary surfaces are allowed when the user explicitly investigates an artifact and must collapse cleanly back into the ambient object.
5. Observer and Builder must be visually distinguishable at 32 px without labels.
6. Spawn animation must visibly originate from GradientAnchor.
7. Closing/collapse should reverse spatially rather than abruptly disappear.
8. Animations must remain smooth while Codex text streams.
9. UI must remain usable on a 13-inch laptop viewport.
10. No permanent orchestration graph.
11. No generic SaaS dashboard feel.
12. No raw technical jargon in the default interaction.
13. Technical artifacts remain inspectable through explicit detail actions.
14. All visible animation must correspond to real state.
15. A viewer without narration should understand:
   • Codex was being used normally,
   • Gradient noticed a correction,
   • the user chose Teach lesson,
   • multiple agents began working,
   • they created a lesson/curriculum,
   • the lesson became post-training,
   • the trained model behaved differently.
16. Avoid card-inside-card-inside-card layouts.
17. Metadata must never visually compete with the object’s meaning.
18. Avoid large decorative gradients, glows, and shadows; tiny localized sprite glow / pulse is allowed for expressive state.
19. A deeper disclosure level must reveal a new semantic level, not simply more prose.


If the interface feels like a dashboard, redesign it.


84. FRONTEND BUILD INSTRUCTION FOR ASTRA


Do not ask Astra to “make the UI Grok Bot style.”


Give it:
• the visual references,
• exact component manifest,
• component contracts,
• state machine,
• backend event mapping,
• design tokens,
• motion tokens,
• file structure,
• copy,
• forbidden patterns,
• visual acceptance criteria.


Astra’s responsibility is implementation fidelity and polish, not inventing the design.


Canonical design instruction:


“Do not design screens. Design meaningful objects that reveal more meaning as the user investigates them.”


Gradient itself remains one persistent peripheral object. Motion should preserve continuity where useful, but semantic clarity is more important than animation.


85. DEMO-HARDENED DECISIONS — LOCKED


These survived live demo rehearsal and persist into the real product.
They constrain both the live backend-driven flow and any demo overlay.


A. Sprite-anchored next step


During multi-beat work, the sprite object itself carries the single next
action (GradientLayer `nextBeat`: one pill beside the anchor, e.g.
Continue →). Canonical panels keep their primary buttons (Teach lesson,
Post-train agent, Run proof). No separate static control cards outside
the sprite-anchored surfaces. Demo steppers and future live “pending
action” affordances share this slot; the slot never duplicates a
canonical panel button for the same stage.


B. Single home per object and disclosure level


Each progressive-disclosure surface owns its content exclusively.

Use the same semantic progression across artifacts:

• Summary → what kind of thing was produced.
• Explore → the meaningful objects / patterns inside it.
• Inspect → what one selected object means, why it exists, and why it matters.
• Specification / Evidence → implementation details, raw contracts, verifier data, provenance, hashes, and traces.

Do not expose implementation structure at the summary level merely because the backend records it.

Do not render the same artifact list in two surfaces at once.

When a deeper surface opens, it should feel like the existing object gained depth rather than an unrelated dashboard appearing.

Observer learning objective, training run, and provenance belong in Technical details.
Training Evidence belongs in ProofDrawer when recorded evidence exists.


C. Mode ownership


The desktop shell (main process) owns the live/demo mode. The renderer
pulls it on mount and subscribes to changes; a renderer reload must
restore the persisted mode, never silently drop to live. The tray menu
is the only mode switch. No in-surface mode toggles (no ← Live style
buttons inside lesson surfaces).


D. Anchor extensibility without leakage


GradientAnchor exposes an `onAnchor` veto hook so ambient triggers
(demo takeover, future presence reactions) can observe or preempt the
sprite click without touching shared layout code. Demo-only transport
(demo-type/abort IPC, SendKeys takeover, staged fixtures) stays in the
desktop shell and demo companion. Shared components (`GradientLayer`,
`AgentSprite`, `AgentPeek`, `ProofDrawer`, `TechnicalDetails`) must
remain drivable by real backend events with no demo imports.
