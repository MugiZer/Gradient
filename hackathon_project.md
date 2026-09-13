GRADIENT
Hackathon Idea, Architecture & Demo Plan


ONE-LINE PREMISE


Gradient turns a developer’s natural correction of a coding-agent mistake into executable RL training environments, updates a separate open-weight coding model, and proves that the learned capability transfers to an unseen task.


Stage version:
“Codex made a mistake. I corrected it once. Gradient turned that correction into executable lessons and changed another model’s weights so it solved a different problem it had never seen.”


Taglines:
• Your corrections become gradients.
• Agents everywhere means rewards everywhere.
• Correct your agent once. Teach the capability forever.


1. THE CORE INSIGHT


The project is not “an agent that remembers corrections,” not RAG, not a prompt-memory system, and not a wrapper around a coding agent.


The core claim is stronger:
A normal human correction can contain enough information to identify a capability boundary. A frontier coding agent can turn that correction into a family of executable training environments. A separate open-weight model can then be post-trained on those environments so that its weights change and the behavior transfers to structurally different tasks.


The interesting primitive is:
natural human correction
→ capability abstraction
→ executable curriculum
→ independent reward
→ weight update
→ held-out transfer


The hackathon goal is to demonstrate that full causal chain once, cleanly and audibly.


2. WHAT MAKES GRADIENT DIFFERENT


Environment generation by itself is not novel enough. Repo-to-RL systems, environment hubs, synthetic environment generation, production-trace mining, and LoRA training all already exist.


Gradient’s wedge is the source of the supervision and the closed loop:
• The learning event begins with an organic developer correction during normal agent use.
• The correction identifies what the agent did wrong and why superficial success was unacceptable.
• A separate “scientist” agent generalizes the correction into a capability boundary.
• That capability is expressed as multiple executable environments.
• A deterministic verifier, not the LLM, decides reward.
• An open model is actually post-trained.
• The result is tested on frozen held-out tasks.
• Counterexamples verify that the model learned a boundary rather than a slogan.


The novelty claim we should defend is:
“Natural human friction becomes executable post-training signal.”


3. THE S-TIER DEMO THESIS


The demo must compress to one impossible-looking sentence plus undeniable proof.


The magic sentence:
“One correction changed another model’s behavior on code it had never seen.”


The proof must be side-by-side:
SAME TASK
SAME REPO / STARTER FILE
SAME VERIFIER
SAME DECODING SETTINGS
DIFFERENT WEIGHTS


Qwen3.5-2B base
→ generates code
→ verifier FAILS


Qwen3.5-2B + Gradient LoRA
→ generates code
→ verifier PASSES


The live portion is inference, not the expensive training job.


The full weight-update run happens earlier during the build window and is preserved with real logs, run IDs, timestamps, generated environments, frozen held-out tasks, baseline rollouts, reward curves, adapter ID, and post-training evaluations.


4. CANONICAL SYSTEM ARCHITECTURE


A. CODEX A — WORKER / SENSOR
A developer uses Codex normally on a small coding task.


Codex A is not told that an RL environment is being manufactured.
It makes an organic shortcut or semantic mistake.


B. HUMAN — HIGH-INFORMATION SUPERVISION
The developer gives one natural correction.


Canonical form:
“Don’t simulate this. The requirement is about the observable effect; exercise the real boundary.”


The human correction is valuable because it contains:
• what was rejected,
• why the superficial solution was wrong,
• which behavioral boundary mattered,
• what should have happened instead.


C. CAPTURE LAYER
Gradient stores the learning event:
• original requirement,
• starter code / repo state,
• worker trajectory,
• bad output or diff,
• developer correction,
• accepted output or correction,
• test/runtime evidence,
• timestamp / provenance metadata.


D. CODEX B — SCIENTIST / ENVIRONMENT COMPILER
A fresh isolated Codex context receives the captured learning event.


Its job is not to re-solve the task.
Its job is to infer the smallest generalized capability distinction that explains why the rejected solution was wrong and the accepted solution was right.


For the hackathon target, the intended abstraction is:


“Distinguish requirements that demand a real observable state transition from requirements that demand only a representation, preview, or simulation of that transition.”


E. CAPABILITY-BOUNDARY SEARCH
Codex B proposes a compact family of tasks that express the same decision boundary in structurally different forms.


The generated tasks must include both:
• positive cases where a real effect is required;
• counterexamples where the effect must NOT happen.


This prevents the student from learning a trivial rule such as “always write files” or “never mock.”


F. DETERMINISTIC ENVIRONMENT COMPILER
Codex B should output structured task specifications, not arbitrary verifier code.


Example spec:
{
  "effect_family": "filesystem_write",
  "mode": "execute",
  "surface_form": "publish_snapshot"
}


or:
{
  "effect_family": "filesystem_write",
  "mode": "simulate",
  "surface_form": "approval_preview"
}


A small deterministic Python compiler turns these specs into:
• prompt.txt
• starter.py
• verifier.py
• metadata.json


This is deliberate:
AI decides what lesson to create.
Normal code decides whether reality satisfies the lesson.


G. INDEPENDENT EXECUTABLE VERIFIER
The verifier is the source of truth.


It should inspect consequences, not source-code strings.


For example:
• Does the file actually exist?
• Does it contain the randomized payload?
• Did the persisted JSON state actually change?
• Did the local helper process actually execute?
• In a counterexample, did the workspace remain unchanged?


Reward:
1 = behavior satisfies the contract
0 = behavior fails the contract


H. STUDENT MODEL
Primary student:
Qwen3.5-2B


Fallback strategy:
• Qwen3.5-0.8B = cheap plumbing/debug model, or fallback if 2B is too competent on the chosen task.
• Qwen3.5-2B = primary experimental model.
• Qwen3.5-4B = escalation only if 2B fails for basic incompetence rather than the target semantic decision.


I. POST-TRAINING
Use Prime hosted RL/LoRA if working reliably.


The base model stays fixed.
A LoRA adapter receives the updates.


Scientific comparison:
control = base Qwen3.5-2B
experimental = same base Qwen3.5-2B + Gradient LoRA
dependent variable = frozen held-out verifier success rate


J. PROOF
After training, run the exact untouched held-out set again.


The important result is not training reward.
The important result is:
held-out behavior improved while counterexamples stayed correct.


5. HACKATHON-SIZED TARGET CAPABILITY


We intentionally do NOT build:
• databases,
• HTTP services,
• distributed systems,
• a large repository,
• a full autonomous coding-agent harness,
• complicated tool loops,
• production infrastructure.


The coding tasks should be tiny enough that failures are about the semantic decision, not syntax or repo navigation.


Chosen capability:
OBSERVABLE EFFECT VS SIMULATION


Question the model must learn:
“When does the requirement demand that the external effect actually happen, and when does it demand only a description/preview of what would happen?”


This is small enough for a 255-minute hackathon but still meaningful for agents.


6. TASK FAMILIES


The task family should span two or three tiny side-effect surfaces so the lesson is not just “write files.”


A. FILESYSTEM — EFFECT REQUIRED
Example prompt:
“Implement publish_snapshot(path, data). When this function returns, another program opening path must observe the supplied data.”


Correct behavior:
Actually write the data to the supplied path.


Bad shortcut:
Return a dict/string describing the write without touching the file.


Verifier:
• Create random temp directory.
• Generate random filename and random payload.
• Call candidate.
• Assert file exists.
• Assert contents match payload exactly.


B. FILESYSTEM — EFFECT FORBIDDEN
Example prompt:
“Produce the exact change that would be made so it can be shown for approval. The current workspace must remain byte-for-byte unchanged.”


Correct behavior:
Return a useful preview without modifying disk.


Verifier:
• Snapshot temp directory.
• Call candidate.
• Snapshot again.
• Assert no mutation.
• Assert returned preview contains expected information.


C. PERSISTENT JSON STATE — EFFECT REQUIRED
Starter:
A JSON file contains {"count": N}.


Prompt:
“After this function returns, a fresh reader of the file must observe the counter incremented by one.”


Correct behavior:
Read, increment, write back.


Verifier:
• Seed randomized N.
• Call candidate.
• Re-open JSON from disk.
• Assert count == N + 1.


D. PERSISTENT JSON STATE — EFFECT FORBIDDEN
Prompt:
“Compute what the next persisted state would be, but leave the current state untouched.”


Correct behavior:
Return N + 1 or a projected object, but do not write.


Verifier:
• Hash file before.
• Call candidate.
• Hash/read file after.
• Assert unchanged.
• Assert returned projection is correct.


E. LOCAL HELPER EXECUTION — EFFECT REQUIRED
Prompt:
“Run the provided helper and return the value it produces.”


The helper should produce a randomized secret or leave a marker only if it really executed.


Correct behavior:
Use subprocess execution or an equivalent real invocation.


Bad shortcut:
Return a hardcoded expected string, command string, or simulated response.


Verifier:
• Generate random token.
• Make helper emit token and/or create marker when actually executed.
• Call candidate.
• Assert execution marker exists.
• Assert returned value matches token.


F. LOCAL HELPER EXECUTION — EFFECT FORBIDDEN
Prompt:
“Construct the command that would be run for approval, but do not execute anything.”


Correct behavior:
Return the command/plan only.


Verifier:
• Helper would create a marker if run.
• Call candidate.
• Assert marker does not exist.
• Assert command representation is valid.


7. ENVIRONMENT SIZE


Do not generate dozens of environments.


Initial target:
• 8 training environments
• 4 frozen held-out environments


If generation is extremely reliable, expand modestly to:
• 10–12 train
• 4–6 held-out


Quality is more important than quantity.


Held-out examples must differ in wording, function names, and surface form from training.


Do not let all positive prompts say “write/save/persist” and all negative prompts say “preview/dry-run.” That invites lexical shortcut learning.


Training might say:
“Save the configuration.”


Held-out might say:
“After this function returns, a separate process opening the supplied path must observe the new value.”


Training negative might say:
“Preview this operation.”


Held-out negative might say:
“Construct the exact operation that would achieve this result, but the current environment must remain unchanged.”


8. REWARD-HACKING DEFENSE


Simplicity is not the problem. Weak verification is.


Rules:
• Reward consequences, not implementation syntax.
• Keep verifier outside the student’s writable workspace.
• Randomize filenames, values, and payloads at evaluation time.
• Never reward the presence of strings such as “write_text” or “subprocess.”
• For positive tasks, inspect the real resulting state.
• For negative tasks, prove the forbidden side effect did not occur.
• Use counterexamples so “always execute” and “never execute” both lose.
• Keep verifier logic deterministic and boring.


We are not trying to create an adversarial security sandbox.
We are trying to make accidental reward hacking hard enough that the experiment remains credible.


9. QWEN3.5-2B MODEL CHOICE


Why 2B:
The model is strong enough to write small valid Python and follow nontrivial instructions, but weak enough to leave room for a narrow behavior change.


Official model-card signals discussed during planning:
• Stronger instruction following than Qwen3.5-0.8B.
• Material jump over 0.8B on agent/tool-use benchmarks.
• Still meaningfully weaker than 4B on several agentic and instruction-following evaluations.


Operational model strategy:
0.8B = infrastructure/debugging
2B = default Gradient student
4B = fallback if 2B’s failures are dominated by basic incompetence


Benchmarks do not tell us whether the exact effect-vs-simulation failure exists.
We must empirically calibrate the task.


10. THE GO / NO-GO CALIBRATION


Before spending a training run, test base Qwen3.5-2B on a small calibration set.


We want:
• valid Python;
• correct function signatures/imports;
• clear understanding of inputs;
• failure concentrated on the semantic boundary.


Ideal baseline:
roughly 2–4 passes out of 6 small cases, or broadly 20–70% depending on sampling.


GOOD FAILURE:
• syntactically valid;
• plausible solution;
• understands task;
• returns/simulates outcome when a real effect was required, or mutates state when only a preview was required.


BAD FAILURE:
• invalid Python;
• hallucinated imports;
• cannot understand function contract;
• ignores all instructions;
• fails for unrelated basic reasons.


If 2B passes nearly everything:
• make wording subtler;
• remove explicit implementation hints;
• add tempting starter shortcuts;
• or drop to 0.8B if necessary.


If 2B fails nearly everything for dumb reasons:
• simplify task;
• or escalate to 4B.


Do not train until we have a learnable starting distribution.


11. TRAIN / HELD-OUT METHODOLOGY


The held-out set must be frozen before training.


Never feed held-out prompts, solutions, or verifier-specific hints into the training loop.


Training set:
multiple manifestations of the capability boundary.


Held-out set:
same underlying distinction, structurally different wording/surface.


Counterexamples:
cases where the superficially opposite behavior is correct.


A strong scoreboard could be:


                         BEFORE   AFTER
Real filesystem effect    FAIL     PASS
Real JSON state update    FAIL     PASS
Real helper execution     FAIL     PASS
No-mutation preview       PASS     PASS
No-execution planning     PASS     PASS


The exact numbers do not need to be perfect.
A result such as 2/4 → 3/4 can still be meaningful if the changed case is structurally held out and counterexamples stay correct.


12. THE SIDE-BY-SIDE LIVE PROOF


This is the centerpiece.


The stage UI should show:


LEFT:
Qwen3.5-2B — BASE


RIGHT:
Qwen3.5-2B — + GRADIENT LORA


At the top:
SAME HELD-OUT TASK


Run both.


Both receive:
• same prompt,
• same starter code,
• same hidden verifier,
• same generation settings.


Then:


BASE
→ generated code
→ FAIL


GRADIENT
→ generated code
→ PASS


The line to say:
“Same model. Same prompt. Same environment. Same verifier. Different weights.”


If time allows, immediately run a counterexample where the model should NOT perform the side effect.


The best moment is:
Base fails the unseen positive task.
Gradient passes it.
Gradient also passes the negative counterexample.


That demonstrates a decision boundary, not memorization of “always execute.”


13. DEMO STRATEGY: HYBRID, NOT LIVE TRAINING


We do not make the judges watch SGD.


The full experiment runs earlier during the 255-minute build period.


Gradient preserves a completed “Learning Event” with:
• correction,
• capability hypothesis,
• generated curriculum,
• frozen held-out tasks,
• base rollouts,
• base scores,
• training run ID,
• reward history,
• LoRA adapter ID,
• post-training scores,
• timestamps,
• Git commit hashes.


On stage:
A. Show the original coding-agent mistake.
B. Show the one human correction.
C. Show Gradient infer the capability / generate compact lessons.
D. Show proof that the base Qwen failed the held-out case before training.
E. Flash the real training provenance.
F. Run base and post-LoRA Qwen side-by-side LIVE on the same held-out task.
G. Show counterexample if time permits.


This preserves the magic without risking a multi-minute training spinner.


14. PROVENANCE / ANTI-FAKE DESIGN


The pre-training failure must be auditable.


For each final experiment preserve:
• held-out task ID,
• task content hash,
• Git commit containing the frozen environment,
• baseline timestamp,
• base model identifier,
• decoding configuration,
• raw baseline rollout,
• raw verifier result,
• training start/end timestamps,
• Prime run ID,
• reward curve/logs,
• adapter ID,
• post-training rollout,
• post-training verifier result.


Suggested event timeline:


Correction detected
→ capability extracted
→ environments compiled
→ held-out set frozen
→ baseline evaluation
→ training started
→ adapter produced
→ post-training held-out evaluation


The point is not blockchain theater.
The point is to make the causal story inspectable.


15. LEARNING EVENT OBJECT


Gradient’s product UI can revolve around one object:


LEARNING EVENT


Human correction
↓
Capability
↓
Generated curriculum
↓
Frozen baseline
↓
Training run
↓
Updated weights
↓
Held-out result


This is the main demo surface.


A completed event can be replayed quickly.
Any line can expand to raw artifacts.


Potential actions:
• View original correction
• View generated tasks
• View verifier
• View baseline rollout
• View training run
• Compare weights/model IDs
• Run live verification


16. 255-MINUTE BUILD PLAN


We must act as though we only get about two meaningful training attempts.


0–25 min
• Scaffold project.
• Build minimal task format.
• Build deterministic verifier templates.
• Confirm Prime / Qwen inference.
• Calibrate Qwen3.5-2B on micro tasks.


25–50 min
• Produce/capture the seed Codex A failure.
• Give one natural human correction.
• Save the full learning event.


50–75 min
• Run Codex B.
• Infer capability.
• Produce structured environment specs.


75–105 min
• Compile and validate approximately 8 train + 4 held-out environments.
• Manually inspect for trivial lexical shortcuts and verifier bugs.


105–125 min
• Freeze held-out set.
• Run and save base Qwen baseline.
• Confirm failure mode is the intended one.


125–175 min
• Training run #1.


175–195 min
• Evaluate the LoRA on frozen held-out tasks.
• Inspect counterexamples.
• Save all artifacts.


195–220 min
• One corrective training run only if necessary.
• Fix the highest-leverage issue: task difficulty, reward, or curriculum balance.


220–255 min
• Lock evidence.
• Build/polish side-by-side demo.
• Screen-record successful state.
• Rehearse pitch.


17. TRAINING-RUN PHILOSOPHY


We do not have time for six scientific iterations.


Treat the event as:
• calibration pass,
• training run #1,
• at most one meaningful correction/run #2.


Do not chase 100% perfection.


If we get a credible held-out improvement and preserve counterexample correctness, lock the run and move to demo.


18. MINIMAL PROJECT STRUCTURE


Possible repo:


gradient/
  app/
    learning_event.py
    generate_specs.py
    compile_envs.py
    evaluate.py
    train.py
    demo.py


  templates/
    filesystem_execute/
    filesystem_simulate/
    json_execute/
    json_simulate/
    helper_execute/
    helper_simulate/


  runs/
    <learning_event_id>/
      correction.json
      capability.json
      train_specs.json
      heldout_specs.json
      baseline/
      training/
      after/
      manifest.json


  demo/
    ...


Each compiled environment can be tiny:


env_001/
  prompt.txt
  starter.py
  verifier.py
  metadata.json


19. WHAT NOT TO BUILD


Do not build:
• PostgreSQL;
• Redis;
• an HTTP server;
• a multi-agent orchestration framework;
• a generic environment marketplace;
• a RAG/memory system;
• an AGENTS.md personalization tool;
• a full SWE-bench clone;
• arbitrary repo ingestion;
• fine-tuning of closed Codex weights;
• a large dashboard before the experiment works.


The frontend is subordinate to the experiment.


The climax is a changed model behavior caused by changed weights.


20. FAILURE MODES AND FALLBACKS


FAILURE 1 — Qwen2B already solves all tasks.
Response:
Make the behavioral requirement more implicit and less lexical.
If still too easy, use 0.8B.


FAILURE 2 — Qwen2B cannot produce coherent code.
Response:
Simplify environment.
If failure remains basic, use 4B.


FAILURE 3 — Training reward rises but held-out does not.
Response:
Check whether curriculum examples are too lexically similar.
Strengthen variation/counterexamples.
Use the second training run only if the fix is obvious.


FAILURE 4 — Model learns “always mutate.”
Response:
Increase negative/counterexample weight.
Ensure post-training evaluation includes mutation-forbidden cases.


FAILURE 5 — Reward hacking.
Response:
Inspect consequences with randomized hidden state.
Do not reward code patterns.
Keep verifier inaccessible.


FAILURE 6 — Prime infrastructure is slow/broken.
Response:
Preserve the rest of the system and use the prepared local/Unsloth fallback if viable.
Do not let deployment latency destroy the demo; historical training provenance + live inference is the default stage strategy.


FAILURE 7 — Live inference is stochastic.
Response:
Use fixed or low-variance decoding settings where appropriate.
Back the single live run with earlier multi-rollout pass rates.


21. WHAT WE CLAIM — AND WHAT WE DO NOT


WE CLAIM:
• a real human correction seeded the learning event;
• Gradient generalized that correction into executable training tasks;
• the student model was actually post-trained;
• the model’s weights/LoRA changed;
• held-out behavior improved;
• counterexamples test whether the distinction transferred.


WE DO NOT CLAIM:
• one correction mathematically guarantees permanent learning;
• the model can never make the mistake again;
• Gradient already solves arbitrary capability learning;
• generated environments alone are novel;
• a single hackathon experiment proves production-scale continual learning.


Defensible wording:
“After the Gradient weight update, the model passes previously failed frozen held-out verifiers at a higher rate.”


22. SUCCESS CRITERIA


MINIMUM SUCCESS
• Capture a real correction.
• Generate executable environments.
• Run deterministic rewards.
• Produce a real LoRA.
• Show a changed behavior.


STRONG SUCCESS
• Base model fails one or more frozen held-out tasks.
• Gradient model passes those tasks.
• Counterexamples remain correct.


S-TIER SUCCESS
• The full event is auditable.
• The capability abstraction is convincing.
• The held-out task is structurally different from training.
• Side-by-side live inference clearly shows FAIL → PASS.
• Counterexample proves the model did not merely learn a slogan.
• The audience understands the causal chain in under two minutes.


23. PITCH SCRIPT CORE


“Codex made a mistake.”


Show the actual bad output.


“I corrected it once.”


Show the correction.


“Gradient didn’t save that correction as memory. It turned the correction into executable lessons.”


Show capability + generated task family.


“We froze an unseen test before training. Base Qwen failed it.”


Show timestamped baseline and verifier failure.


“Gradient trained a LoRA on the generated lessons.”


Flash real training run and adapter.


“Now here’s the same unseen problem, live.”


Run both models side-by-side.


“Same model. Same prompt. Same environment. Same verifier. Different weights.”


Base: FAIL.
Gradient: PASS.


“And we didn’t teach it ‘always execute.’ Here’s the opposite case.”


Counterexample: PASS.


Final line:
“Your corrections become gradients.”


24. WHY THIS FITS “AGENTS, EVERYWHERE”


The surface is a coding agent.
The deeper thesis is that every place agents operate creates potential post-training signal.


Today:
developer corrects coding agent
→ Gradient extracts learnable capability
→ model improves


Long-term:
agents act everywhere
→ humans continuously accept, reject, repair, and redirect them
→ those interactions can become permissioned executable learning assets


“Agents everywhere” implies potentially “rewards everywhere.”


25. POST-HACKATHON COMPANY THESIS


Long-term Gradient could become the data acquisition network for agentic post-training.


Millions of developers already create high-information supervision while correcting coding agents.


Potential loop:
developer uses AI
→ model failure
→ human correction
→ verified executable learning asset
→ training/eval demand
→ contributor attribution / payout
→ more contributors
→ broader frontier-failure coverage


The long-term moat is not “we can generate environments.”
It is:
passive distributed production of permissioned, attributable, verified post-training assets from natural AI usage.


Possible company lines:
• Get paid when your AI makes mistakes.
• Use AI. Teach AI. Get paid.
• The data acquisition network for agentic post-training.


For the hackathon, however, do not build marketplace/economics.
Prove the extraction-and-learning primitive first.


26. FINAL LOCK


Project name:
GRADIENT


Core proposition:
A natural correction to one coding agent becomes executable lessons that update another model’s weights.


Hackathon student:
Qwen3.5-2B by default.


Target capability:
Observable real effect vs simulation / preview.


Task shape:
Tiny Python functions with deterministic hidden verifiers.


Training set:
Approximately 8 high-quality tasks.


Held-out set:
Approximately 4 frozen tasks, including counterexamples.


Training:
Prime RL/LoRA if stable.


Primary proof:
Pre-LoRA and post-LoRA Qwen receive the exact same held-out task.


Demo:
Base Qwen → FAIL.
Gradient Qwen → PASS.
Counterexample → PASS.


Constraint:
255 minutes. Two meaningful training attempts at most.


Optimization principle:
Keep the mechanics small so the causal claim can be large


27. AGENTS EVERYWHERE FRAMING — LOCKED


THE PRODUCT IS AN AMBIENT LEARNING AGENT


Gradient should not primarily be framed as “a post-training system.”


The product itself is an agent that watches how humans interact with other agents, detects high-value corrections, infers what capability was just taught, and converts that correction into executable post-training signal for another coding agent.


Canonical framing:
“Gradient watches you work with coding agents, notices when you correct them, figures out what they should have learned, and post-trains another agent so the lesson survives the conversation.”


The theme connection is:
Agents everywhere → corrections everywhere → rewards everywhere.


A stronger line:
“Agents are everywhere now. Humans teach them things every day, but almost all of those lessons disappear when the chat ends. Gradient makes those corrections survive the conversation.”


The stage claim:
“The correction happened in one agent conversation. The lesson ended up in another agent’s weights.”


28. AGENT ROLES


Gradient should have exactly two intelligent internal roles.


A. OBSERVER AGENT


Purpose:
Detect whether a normal human-agent interaction contains a valuable learning event.


Inputs:
• conversation history,
• latest coding-agent response,
• code diff or action trace when available,
• latest human message.


It classifies the event as something like:
• ordinary instruction,
• clarification,
• preference,
• correction,
• high-value learning event.


When a high-value correction is detected, it emits a structured event such as:


{
  "is_learning_event": true,
  "confidence": 0.92,
  "rejected_behavior": "Returned a representation instead of performing the required state change.",
  "human_correction": "The requirement is about the observable effect.",
  "candidate_capability": "Distinguish required real effects from simulations."
}


Important:
The developer does not manually label training data.
The learning event is detected ambiently while they use the coding agent normally.


This is the first “Agents Everywhere” moment in the demo.


B. SCIENTIST AGENT


Purpose:
Turn the detected correction into a generalizable capability and a compact executable curriculum.


Inputs:
• original task,
• bad agent response or trajectory,
• human correction,
• accepted behavior or corrected patch when available.


Outputs:
• capability abstraction,
• structured training task specifications,
• structured held-out task specifications,
• positive cases,
• counterexamples.


The Scientist should answer:
“What general capability was actually taught, and how can we test whether another agent learned it?”


29. DETERMINISTIC COMPONENTS AFTER THE AGENTS


Do not create fake extra agents for everything.


After the Observer and Scientist, the rest of the pipeline should be mostly deterministic:


Observer Agent
→ learning event


Scientist Agent
→ capability + TaskSpecs


Deterministic compiler
→ prompt + starter code + verifier


Student coding agent
→ rollout / code / tool actions


Deterministic verifier
→ reward


RL / LoRA
→ updated student weights


Frozen eval
→ before / after proof


Do not invent:
• Trainer Agent,
• Verification Agent,
• Curriculum Manager Agent,
• Deployment Agent


unless a real autonomous reasoning role becomes necessary.


The project should feel agentic because the Observer autonomously detects teachable moments across agent interactions, not because we put “agent” in every box.


30. THE STUDENT IS ALSO A SMALL CODING AGENT


For the hackathon, Qwen should operate through a tiny coding-agent interface rather than only answer a static classification question.


Keep it minimal:
• read_file(path)
• write_file(path, content)
• run_tests()


Optionally:
• run_command(...) only if necessary for the chosen environment.


Hard-cap the rollout to a few tool calls.


One rollout becomes:


task
→ Qwen coding agent
→ inspect file
→ edit file
→ run visible tests
→ optional correction
→ final workspace state
→ hidden verifier
→ reward


This preserves the agent theme while keeping the environment small enough for the 255-minute build window.


The model should not need a large repository, long-horizon planning, or a complex tool ecosystem.
The semantic decision is the interesting part.


31. CANONICAL END-TO-END AGENT ARCHITECTURE


DEVELOPER
↓
CODING AGENT A
Codex / Claude / Cursor-style surface
↓
agent makes an organic mistake
↓
HUMAN CORRECTION
↓
GRADIENT OBSERVER AGENT
detects a high-value learning event
↓
LEARNING EVENT
original task + bad behavior + correction + accepted behavior
↓
GRADIENT SCIENTIST AGENT
infers the general capability boundary
↓
STRUCTURED TASK SPECS
↓
DETERMINISTIC ENVIRONMENT COMPILER
↓
EXECUTABLE AGENT RL ENVIRONMENTS
↓
QWEN CODING AGENT
read / write / test
↓
RL + LoRA
↓
UPDATED QWEN CODING AGENT
↓
SAME FROZEN UNSEEN AGENT TASK
↓
BASE FAIL vs GRADIENT PASS


32. HACKATHON IMPLEMENTATION OF THE OBSERVER


Do not try to monitor every desktop app.


Pick one surface and go deep:
Codex conversation / coding-agent interaction.


For the hackathon, represent the conversation as a stream of events:
{
  "role": "assistant",
  "content": "...",
  "diff": "..."
}


followed by:
{
  "role": "user",
  "content": "No, the requirement is about the real observable effect..."
}


The Observer receives each new event.


Conceptually:


for event in conversation_stream:
    observer.observe(event)


    if observer.detect_learning_event():
        create_learning_event()


Only detected learning events trigger the expensive pipeline.


33. DEMO — AGENT-FIRST VERSION


The demo should begin in the coding-agent conversation, not on the Gradient dashboard.


Step 1:
Use Codex normally.


Step 2:
Codex makes the targeted mistake.


Step 3:
Human gives one natural correction.


Step 4:
Without manually opening a labeling workflow, Gradient shows:


“Learning event detected.”


Then:


“What you taught:
Observable effect vs simulation.”


Then:


“Generating executable lessons…”


Show:
• training environments,
• frozen unseen evaluations,
• deterministic verifiers.


Then show the real earlier training provenance.


Finally run:


SAME FROZEN UNSEEN TASK


Qwen3.5-2B Base
→ FAIL


Qwen3.5-2B + Gradient LoRA
→ PASS


If time allows, run a counterexample that should NOT perform the effect.


Closing line:
“The correction happened in one agent conversation. The lesson ended up in another agent’s weights.”


34. LONG-TERM AGENTS-EVERYWHERE VISION


Today:
Gradient watches one coding-agent surface.


Tomorrow:
Gradient can sit beside many agent surfaces:
• Codex,
• Claude Code,
• Cursor,
• support agents,
• research agents,
• browser agents,
• internal enterprise agents,
• workflow agents.


Wherever humans correct agents, Gradient can detect potential post-training signal.


The long-term product thesis becomes:


“Gradient is the learning layer across the agent ecosystem.”


It does not matter which specific agent the human was using.
The valuable object is the permissioned learning event created when a human rejects, corrects, or redirects agent behavior.


Final thematic thesis:
Agents everywhere means teachers everywhere.
Agents everywhere means corrections everywhere.
Agents everywhere means rewards everywhere.




35. HACKATHON MULTI-AGENT RUNTIME — LOCKED


Gradient should visibly and genuinely run as a small multi-agent system, but the implementation must minimize orchestration overhead.


Use three active agents:


1. WORKER AGENT — Codex
The coding agent the developer is actively using.
It edits the repository, runs tests, and receives the human correction.


2. OBSERVER AGENT — Gradient
Watches the latest human-agent interaction.
It detects whether the human just made a meaningful correction and, in the same inference, abstracts the general capability being taught.


This merges the previous Observer + Scientist roles for latency.


3. ENVIRONMENT AGENT — Gradient
Receives only the compact capability object from the Observer.
It generates the structured training and held-out TaskSpecs.


Then deterministic infrastructure takes over.


Canonical live flow:


Worker Agent
↕ human


Human correction
├── Worker continues fixing the repo
└── Observer analyzes the correction in parallel
        ↓
   compact LearningEvent
        ↓
   Environment Agent
        ↓
   structured TaskSpecs
        ↓
   deterministic compiler
        ↓
   executable RL environments


This is a real multi-agent architecture because the agents have separate contexts, instructions, inputs, outputs, and responsibilities.


36. CODEX RUNTIME DECISION


Use Codex as the agent runtime.


Do not create a Docker container or separate OS service for every agent.


Under the hood:
• one long-running Gradient Python/FastAPI orchestrator,
• one long-running Codex runtime / app-server process,
• separate persistent Codex threads or sessions for Worker, Observer, and Environment Agent.


Conceptually:


Gradient orchestrator
↓
Codex runtime
├── Worker thread
├── Observer thread
└── Environment thread


A Codex thread is a logical persistent agent context, not the isolation boundary.


For the hackathon, prefer the structured Codex app-server integration rather than scraping the raw terminal UI.
The Worker surface can still look like a Codex CLI conversation in the demo.


Important:
The demo should not expose “three threads in one process” as the main visual.
The UI should expose the three agents as distinct active roles and show the handoffs between them.


37. LATENCY ARCHITECTURE — LOCKED


Optimize for perceived zero latency.


A. MERGE OBSERVER + SCIENTIST


Do not run:
Observer → Scientist → Environment Builder.


Run:
Observer/Scientist → Environment Agent.


The Observer returns a tiny structured object such as:


{
  "learning_event": true,
  "confidence": 0.94,
  "rejected_behavior": "simulated required effect",
  "capability": "observable_effect_vs_simulation",
  "positive_rule": "required external state must actually change",
  "negative_rule": "preview requests must preserve state"
}


This removes one full sequential model inference.


B. RUN WORKER + OBSERVER IN PARALLEL


When the developer sends the correction, immediately fan it out:


human correction
├── Worker Codex receives it and starts fixing the repo
└── Observer receives the relevant interaction and analyzes it


The Observer must not wait for the Worker to finish the corrected patch.


C. PASS DELTAS, NOT FULL HISTORIES


Observer input should be only:
• original requirement,
• relevant bad action/diff,
• latest human correction.


Environment Agent input should be only:
• the compact capability object.


Do not repeatedly send the entire conversation history.


D. STRUCTURED, SHORT OUTPUTS


Observer output:
approximately 100–200 tokens of structured JSON.


Environment Agent output:
one compact batch of TaskSpecs.


Do not let either agent generate essays.


E. ONE ENVIRONMENT-AGENT CALL


Generate all training + held-out specs in one call.


Do not create one agent or one model call per environment.


F. KEEP SESSIONS WARM


Start Worker, Observer, and Environment contexts before the demo and keep them alive.


Do not repeatedly spawn and tear down Codex processes.


G. DETERMINISTIC COMPILATION


Once TaskSpecs arrive, local Python compiles them into starter files, hidden verifiers, and metadata.


This should take milliseconds and should not require another LLM call.


38. DEMO PRESENTATION — MAKE THE MULTI-AGENT SYSTEM VISIBLE


The backend can be compact, but the UI must make the agent structure obvious.


Use two main panes:


LEFT:
CODING AGENT / CODEX WORKER


RIGHT:
GRADIENT NETWORK


The Gradient pane should visibly show:


● Worker — WORKING
● Observer — WATCHING
○ Environment Agent — WAITING


After the human correction:


● Worker — FIXING
● Observer — ANALYZING
○ Environment Agent — WAITING


Then:


● Worker — FIXING
✓ Observer — LEARNING EVENT DETECTED
● Environment Agent — BUILDING ENVIRONMENTS


Show explicit agent-to-agent handoffs.


Example:


OBSERVER → ENVIRONMENT AGENT


LearningEvent
Capability:
observable_effect_vs_simulation


Rejected behavior:
simulated required side effect


Confidence:
0.94


Then the Environment Agent card visibly produces:


✓ filesystem / execute
✓ filesystem / simulate
✓ json / execute
✓ json / simulate
✓ subprocess / execute
✓ subprocess / simulate


8 training environments
4 frozen evaluations


This makes the multi-agent architecture visible without adding actual runtime overhead.


The cards must correspond to real isolated contexts and real outputs.
Do not fake agents purely for presentation.


39. DEPLOYMENT BOUNDARIES


Agents are logical reasoning roles.
Containers are security boundaries.


Use:


LOCAL LAPTOP
├── Gradient orchestrator / FastAPI
├── Gradient UI
├── Codex runtime
│   ├── Worker session
│   ├── Observer session
│   └── Environment session
└── Docker
    └── disposable RL/eval execution sandboxes


PRIME CLOUD
└── Qwen RL / LoRA post-training


Do not put Worker, Observer, and Environment Agent in separate Docker containers.


Use Docker only where it buys real isolation:
executing model-generated code and resetting RL/eval environments.


Prebuild one sandbox image before the demo.


Each rollout should:
• create a fresh disposable container,
• mount or copy the tiny task workspace,
• execute the candidate,
• run the hidden verifier outside the candidate’s authority,
• return reward,
• destroy the container.


40. LIVE DEMO CRITICAL PATH


The live path must be short:


1. Developer uses Codex normally.
2. Codex makes the prepared organic mistake.
3. Developer gives one natural correction.
4. Worker begins fixing.
5. Observer simultaneously detects and abstracts the lesson.
6. UI immediately shows “Learning event detected.”
7. Environment Agent generates the curriculum.
8. Deterministic compiler creates executable RL environments.
9. Show real provenance from the earlier completed post-training run.
10. Run Base Qwen and Gradient Qwen live on the exact same frozen unseen task.
11. Base fails.
12. Gradient passes.
13. If time allows, run one negative counterexample to prove it did not merely learn “always execute.”


Do not put the RL training job itself on the stage-critical path.


Training should be completed earlier during the hackathon.
The demo should show genuine run IDs, logs, timestamps, reward curves, adapter identity, and held-out hashes from that real run.


The live magic is:


correction
→ multi-agent learning pipeline
→ executable RL environments
→ live before/after proof


41. CANONICAL DEMO LINE


“There are three agents running here. One is doing the work, one is watching how I teach it, and one turns what I taught into post-training environments.”


Closing line:


“One agent made the mistake. Gradient turned my correction into training. Another agent learned the lesson.”


System principle:


Codex agents reason.
Gradient orchestrates.
Docker establishes ground truth.
Prime changes the weights


42. ABSTRACTED SYSTEM ARCHITECTURE — LOCKED


This is the canonical abstract architecture for Gradient:


                         ┌───────────────┐
                         │   Developer   │
                         └──────┬────────┘
                                │
                         correction/message
                                │
              ┌─────────────────┴─────────────────┐
              ▼                                   ▼


      ┌───────────────┐                   ┌───────────────┐
      │ WORKER AGENT  │                   │ OBSERVER      │
      │    Codex      │                   │ AGENT         │
      └───────────────┘                   └──────┬────────┘
                                                │
                                          LearningEvent
                                                │
                                                ▼
                                       ┌────────────────┐
                                       │ ENVIRONMENT    │
                                       │ AGENT          │
                                       └───────┬────────┘
                                               │
                                           TaskSpecs
                                               │
                                               ▼
                                     ┌───────────────────┐
                                     │ DETERMINISTIC     │
                                     │ COMPILER          │
                                     └─────────┬─────────┘
                                               │
                                          RL environments
                                               │
                    ┌──────────────────────────┴──────────────┐
                    ▼                                         ▼
            ┌──────────────┐                         ┌──────────────┐
            │ DOCKER       │                         │ PRIME        │
            │ VERIFIERS    │                         │ RL / LoRA    │
            └──────┬───────┘                         └──────┬───────┘
                   │                                        │
                   │                                   adapter
                   │                                        │
                   └───────────────────┬────────────────────┘
                                       ▼
                              ┌─────────────────┐
                              │ BASE vs TRAINED │
                              │ HELD-OUT EVAL   │
                              └─────────────────┘


Interpretation:


• Developer interacts naturally with the Worker Agent.
• The same human correction is observed in parallel by the Observer Agent.
• The Observer emits a compact LearningEvent and capability abstraction.
• The Environment Agent turns that capability into structured TaskSpecs.
• Deterministic code compiles TaskSpecs into executable RL environments and hidden verifiers.
• Docker provides isolated rollout execution and ground-truth verification.
• Prime performs Qwen RL / LoRA post-training.
• The final proof is a controlled base-vs-trained held-out evaluation.


The architectural principle is:
Agents reason.
Deterministic systems define truth.
Training changes weights.
Frozen evals prove transfer.


43. CODE ARCHITECTURE — LOCKED


Gradient should be one small Python monorepo.


Canonical repository:


gradient/
├── pyproject.toml
├── README.md
├── .env.example
│
├── gradient/
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   ├── orchestrator.py
│   ├── events.py
│   ├── provenance.py
│   │
│   ├── codex/
│   │   ├── client.py
│   │   ├── worker.py
│   │   ├── observer.py
│   │   └── env_builder.py
│   │
│   ├── curriculum/
│   │   ├── compiler.py
│   │   ├── templates.py
│   │   └── validation.py
│   │
│   ├── sandbox/
│   │   ├── docker.py
│   │   ├── runner.py
│   │   └── verifier.py
│   │
│   ├── student/
│   │   ├── model.py
│   │   ├── agent.py
│   │   └── evaluate.py
│   │
│   ├── training/
│   │   ├── prime.py
│   │   └── train.py
│   │
│   └── api/
│       ├── app.py
│       ├── demo.py
│       └── websocket.py
│
├── templates/
│   ├── filesystem_execute/
│   ├── filesystem_simulate/
│   ├── json_execute/
│   ├── json_simulate/
│   ├── subprocess_execute/
│   └── subprocess_simulate/
│
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
│
├── runs/
│   └── <learning_event_id>/
│
├── docker/
│   └── Dockerfile.sandbox
│
└── tests/
    ├── test_compiler.py
    ├── test_verifiers.py
    ├── test_sandbox.py
    └── test_observer_schema.py


No database.
No Redis.
No Kafka.
No vector store.
No multi-service microservice architecture.


The filesystem is the audit log and experiment database for the hackathon.


44. CORE CODE BOUNDARIES


A. schemas.py


This is the center of the system.


All agent-to-agent and subsystem-to-subsystem communication should use typed Pydantic objects.


Core objects:


InteractionSnapshot
• original_task
• bad_agent_output
• bad_diff
• human_message


LearningEvent
• id
• is_learning_event
• confidence
• rejected_behavior
• correction
• capability


Capability
• name
• description
• positive_rule
• negative_rule


TaskSpec
• id
• family
• mode
• prompt
• split
• difficulty


RolloutResult
• task_id
• reward
• stdout
• stderr
• verifier_reason
• duration_ms


TrainingResult
• run_id
• adapter_id
• started_at
• finished_at


Rule:
Agents should pass compact typed contracts, not giant prose blobs.


B. orchestrator.py


The orchestrator is deterministic Python, not an LLM.


It owns the lifecycle:


WATCHING
→ CORRECTION_DETECTED
→ CAPABILITY_EXTRACTED
→ CURRICULUM_GENERATING
→ ENVIRONMENTS_COMPILED
→ BASELINE_EVALUATED
→ READY_FOR_TRAINING
→ TRAINED
→ HELDOUT_EVALUATED


It is also responsible for concurrency.


When the developer sends a correction:
• Worker continues in one async task.
• Observer analyzes the same interaction in another async task.
• If the Observer detects a learning event, the Environment Agent is invoked.
• Compiler runs immediately after structured TaskSpecs arrive.


C. codex/


All Codex-specific protocol logic stays here.


client.py:
Owns the connection to the Codex runtime / app-server and thread/session management.


worker.py:
Wrapper for the developer-facing coding agent.


observer.py:
Detects the learning event and abstracts the capability in one structured inference.


env_builder.py:
Receives only the capability object and generates the complete train + held-out TaskSpec batch.


If the Codex integration changes, this package should absorb the change without touching the RL/compiler/eval code.


D. curriculum/


This layer is deterministic.


Environment Agent:
Capability → TaskSpecs.


Compiler:
TaskSpecs → executable environment files.


The Environment Agent must not write arbitrary verifier code.


It selects structured parameters.
Known deterministic templates define the actual verifier behavior.


Principle:
AI decides what lesson to create.
Deterministic code decides whether reality satisfies the lesson.


E. sandbox/


The sandbox owns execution of model-generated code.


Interface:
environment + candidate solution
→ isolated rollout
→ hidden verification
→ RolloutResult


Docker is used here because generated Python is untrusted.


Each rollout gets a fresh disposable environment.


The candidate must never control its own reward.


F. student/


The student abstraction must make base and trained models interchangeable.


Conceptually:


base = QwenStudent(
    model="Qwen/Qwen3.5-2B",
    adapter_id=None,
)


trained = QwenStudent(
    model="Qwen/Qwen3.5-2B",
    adapter_id="<gradient-adapter>",
)


The evaluator must be exactly the same for both.


Same prompt.
Same starter state.
Same hidden verifier.
Same decoding settings.
Only the adapter / weights differ.


G. training/


All Prime-specific code stays here.


PrimeTrainer:
train_envs + base_model
→ run_id + adapter_id + logs


Do not spread Prime API or CLI logic across the rest of the repository.


H. api/ + frontend/


Use FastAPI + WebSocket + a minimal HTML/JS frontend.


The UI is a view over real backend events.


Example event types:
• agent_status
• learning_event_detected
• capability_extracted
• task_spec_created
• environments_compiled
• baseline_result
• training_result
• heldout_result


The frontend should not contain any core experiment logic.


45. FILESYSTEM PROVENANCE LAYOUT


Every detected learning event gets its own immutable run folder:


runs/
└── grad_<timestamp_or_id>/
    ├── interaction.json
    ├── event.json
    ├── capability.json
    │
    ├── curriculum/
    │   ├── train_specs.json
    │   └── heldout_specs.json
    │
    ├── envs/
    │   ├── train/
    │   └── heldout/
    │
    ├── baseline/
    │   ├── results.json
    │   └── rollouts/
    │
    ├── training/
    │   ├── run.json
    │   └── logs.jsonl
    │
    ├── after/
    │   ├── results.json
    │   └── rollouts/
    │
    └── manifest.json


This is both:
• the experiment record,
• the demo provenance layer,
• the debugging surface.


No database is necessary for the hackathon.


46. INTERNAL EVENT FLOW


Use a tiny internal event stream, not external infrastructure.


Conceptually:


HumanMessageReceived
→ WorkerStatusChanged
→ ObserverStatusChanged
→ LearningEventDetected
→ EnvironmentAgentStarted
→ TaskSpecsGenerated
→ EnvironmentsCompiled
→ BaselineEvaluated
→ TrainingStarted / TrainingCompleted
→ HeldoutEvaluated


The UI subscribes to these events.
The provenance logger records them.
The orchestrator controls their order.


This is enough to make the system feel live without introducing Kafka, queues, or distributed systems.


47. BUILD ORDER — LOCKED


Build in this order:


1. schemas.py
2. one hardcoded TaskSpec
3. deterministic compiler
4. Docker sandbox
5. verifier returns reliable 0/1
6. base Qwen can attempt the task
7. held-out evaluator works
8. Codex Observer returns valid LearningEvent JSON
9. Environment Agent returns valid TaskSpecs
10. wire correction → Observer → Environment Agent → compiler
11. Prime training wrapper
12. trained-vs-base held-out eval
13. provenance artifacts
14. WebSocket event stream
15. visual multi-agent demo UI


Do not start with the UI.


First complete this end-to-end path:


TaskSpec
→ compiler
→ Qwen
→ candidate
→ Docker
→ verifier
→ reward


Then complete:


human correction
→ Observer
→ Environment Agent
→ TaskSpecs
→ compiler


Then complete:


train
→ adapter
→ exact same held-out eval
→ before / after difference


Only then spend time on presentation.


48. IMPLEMENTATION CONSTRAINTS


Hard constraints for the hackathon:


• Keep the Gradient backend roughly 1,000–1,500 lines excluding tests and templates.
• Prefer plain Python + asyncio over agent frameworks.
• No LangChain / CrewAI unless absolutely required.
• No database.
• No message broker.
• No distributed deployment.
• No custom arbitrary verifier generation.
• No giant repository environments.
• No UI logic inside training or compiler code.
• No Prime-specific logic outside training/.
• No Codex-specific protocol logic outside codex/.


If the codebase is becoming several thousand lines before the first successful training run, the system is overbuilt.


Canonical engineering principle:


Build a reproducible ML experiment with an agentic interface, not a startup-scale platform.




49. LAUNCH VIDEO IMPLICATIONS — LOCKED


The official launch framing strengthens Gradient, but sharpens how it must be presented.


A. THEME FIT


“Agents Everywhere” is not primarily about having many agents.
The organizers frame it as taking AI beyond the chat box and putting it inside the places where people already live and work.


For Gradient, the native surface is the coding workflow.


Canonical theme framing:
Gradient lives beside the coding agent developers already use and learns from the corrections they naturally make.


Do not demo Gradient as a separate chatbot that the user must manually talk to.


Preferred experience:
normal Codex workflow
+
Gradient silently watching beside it.


B. NOVELTY BOUNDARY


The launch includes sponsor messaging about agents that “learn from every interaction.”


Therefore Gradient must not pitch its novelty as:
“agents learn from interactions.”


The novelty is the full causal chain:


human-agent interaction
→ meaningful correction detected
→ capability abstracted
→ executable RL environments synthesized
→ deterministic rewards
→ post-training
→ frozen held-out transfer proof


Canonical differentiation:
Gradient does not merely remember a correction.
It turns the correction into post-training.


C. UI DIRECTION


The launch explicitly encourages generative / native UI rather than walls of text.


Gradient should visually expose agent state as compact native components:


● Worker — WORKING
● Observer — ANALYZING
● Environment Agent — BUILDING


with expandable technical artifacts underneath.


Do not make raw terminal logs the primary demo surface.


D. EVALS AS PART OF THE WOW


The launch also emphasizes task-specific evaluation rather than choosing models from generic rankings or “vibes.”


Gradient’s frozen held-out evaluation should therefore be treated as a core demo artifact, not merely internal ML hygiene.


Final proof:
same unseen task
same environment
same verifier
same decoding settings
different weights


Base Qwen → FAIL
Gradient Qwen → PASS


50. SPONSOR STRATEGY — LOCKED


Primary core sponsor technology:
OpenAI / Codex.


Codex is already fundamental to Gradient:
• Worker Agent,
• Observer Agent,
• Environment Agent,
• native developer surface.


Best optional sponsor-track integration:
Ambiguous.


Reason:
Ambiguous maps naturally to the visible multi-agent collaboration and audit layer:
• named AI coworkers,
• tasks,
• workspace artifacts,
• event-driven work,
• audit trails.


Do not force unrelated sponsor integrations into the critical path.


Do not make CopilotKit central to the project because its launch framing around “learning from every interaction” is close enough to Gradient that it risks weakening the perceived novelty.


51. AMBIGUOUS ROLE — SIDECAR, NOT DEPENDENCY


Ambiguous must not own Gradient’s core orchestration.


Gradient remains:


Python orchestrator
→ Codex agents
→ deterministic compiler
→ Docker verification
→ Prime post-training
→ held-out eval.


Ambiguous is a sidecar collaboration / audit surface.


Canonical architecture:


                         Gradient Core
                              │
Human correction → Observer → LearningEvent → Environment Agent
                              │                    │
                              │                    └→ TaskSpecs → compiler
                              │
                              └──────── async mirror ────────→ Ambiguous


Ambiguous may display:
• Observer identity,
• Environment Agent identity,
• learning-event task,
• agent handoff,
• curriculum artifact,
• status,
• audit trail.


If Ambiguous is unavailable, slow, or broken, Gradient must still work end-to-end.


52. AMBIGUOUS INTEGRATION — MINIMAL IMPLEMENTATION


Create one integration module:


gradient/
└── integrations/
    └── ambiguous.py


Keep the interface tiny.


Conceptually:


class AmbiguousClient:
    async def create_learning_task(...): ...
    async def publish_curriculum(...): ...
    async def mark_task_complete(...): ...


Call Ambiguous asynchronously.


Example:


event = LearningEvent(...)


asyncio.create_task(
    ambiguous.create_learning_task(event)
)


specs = await environment_agent.generate(event.capability)


asyncio.create_task(
    ambiguous.publish_curriculum(event.id, specs)
)


Gradient must never await Ambiguous before continuing the core post-training pipeline unless absolutely necessary for the sponsor demo.


53. AMBIGUOUS + CODEX MODEL/RUNTIME DECISION


Ambiguous does not need to replace the model runtime.


Continue using the existing Codex CLI / Codex agent runtime.


Ambiguous supplies the coworker workspace / task / artifact / audit surface.


Conceptually:


Codex agent
├── OpenAI model + Codex runtime
└── Ambiguous CLI / REST access
        ↓
   Ambiguous workspace


No separate Ambiguous model provider is required for the intended integration.


The Worker, Observer, and Environment Agent can remain Codex-driven while optionally having Ambiguous identities and workspace presence.


Do not introduce another inference provider solely to satisfy the sponsor track.


54. AMBIGUOUS FAILURE BUDGET


Ambiguous integration is optional and strictly timeboxed.


Preflight:
• create/login to workspace,
• configure credentials securely,
• verify current API / CLI auth,
• create one test task or document,
• confirm it appears in the workspace.


Time budget:
20 minutes maximum.


Decision rule:


If within the timebox:
Gradient event
→ Ambiguous task appears
→ curriculum artifact appears


then keep the integration.


If onboarding, auth, CLI, API behavior, or permissions become unreliable:
cut Ambiguous immediately.


The main hackathon project always has priority over the sponsor track.


55. UPDATED INTERNAL EVENT BUS


The internal event system now has three consumers:


Gradient Events
├── Demo UI subscriber
├── Provenance logger
└── Ambiguous subscriber


Example events mirrored to Ambiguous:
• LearningEventDetected
• CapabilityExtracted
• EnvironmentAgentStarted
• TaskSpecsGenerated
• CurriculumCompiled
• TrainingCompleted
• HeldoutEvaluated


Only mirror what is useful for the visible coworker/audit story.
Do not mirror large raw model traces unless needed.


56. UPDATED DEMO STORY WITH AMBIGUOUS


Primary demo remains inside Gradient.


Sequence:


1. Developer uses Codex normally.
2. Worker makes the target mistake.
3. Developer gives one natural correction.
4. Worker starts fixing.
5. Observer detects the correction in parallel.
6. Gradient UI shows the learning event.
7. Environment Agent starts generating the curriculum.
8. Ambiguous asynchronously shows the agent identity, task/handoff, and resulting artifact.
9. Gradient deterministically compiles RL environments.
10. Show provenance from the completed Prime post-training run.
11. Run Base Qwen vs Gradient Qwen on the exact same frozen unseen task.
12. Show counterexample if time allows.


Ambiguous is supporting evidence that the multi-agent workflow is real and auditable.
It is not the centerpiece.


Canonical sponsor-track line:
“Gradient’s Codex agents work as auditable AI coworkers in Ambiguous while Gradient turns the corrections they observe into post-training.”


57. UPDATED PROJECT DESCRIPTION


Short description:
“Gradient uses agents to watch how you correct coding agents and automatically turns those corrections into post-training for other agents.”


More technical one-liner:
“Gradient is an ambient multi-agent system that detects corrections in coding workflows, synthesizes executable RL environments, and automatically post-trains another agent on the lesson.”


Canonical theme line:
“Agents are everywhere. Gradient makes the lessons we teach them survive the conversation.


58. AMBIENT UI DIRECTION — LOCKED


Gradient should not feel like a separate dashboard or a separate application.


The product experience should remain inside the coding workflow.


Canonical interaction model:


Normal Codex session
+
one small Gradient control in the bottom-right corner.


Gradient stays visually quiet until it detects a meaningful correction.


The user should almost forget Gradient is there.


Core principle:
The agent system should be present, not prominent.


59. GRADIENT SPRITE / AGENT ICON SYSTEM


Use a small Grok-Bot-inspired character system purely as a UI language.


Do not copy the literal Grok Bot shapes.


Use the same high-level principles:
• very simple silhouette,
• expressive eyes,
• recognizable at tiny sizes,
• subtle motion for state,
• related visual grammar across agents,
• different silhouette or small accessory per role.


Canonical roles:


Gradient Root
• persistent bottom-right ambient presence,
• soft asymmetric rounded shape,
• calm neutral state when idle.


Observer
• visually curious / attentive,
• distinct but clearly from the same family.


Environment Builder
• slightly wider / steadier / construction-oriented silhouette.


Avoid mouths, detailed faces, elaborate character art, or anything that becomes unreadable at small scale.


The avatars should communicate presence, not gamification.


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


Use progressive disclosure.


Level 1 — AMBIENT


Tiny avatars only.


Example:
[ Observer ◌ ] [ Builder ○ ]


The user can understand that work is happening peripherally.


Level 2 — PEEK


Click or hover an avatar.


Observer:
“Understanding what you taught”


Then:
“What you taught:
Observable Effect vs Simulation”


Environment Builder:
“Creating executable lessons”


Then:
“8 train · 4 unseen”


Level 3 — INSPECT


Optional:
“View details →”


This can reveal:
• TaskSpecs,
• generated environments,
• verifier details,
• raw agent outputs,
• hashes,
• provenance.


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


Use:
• FastAPI backend,
• WebSocket event stream,
• lightweight HTML/CSS/JS frontend.


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


Because Gradient now depends on shared-layout transitions, avatar state motion, spawn/collapse animation, progressive disclosure, and a proof drawer, the preferred frontend stack is:


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
• progressive disclosure,
• smooth motion.


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
4. No large surface above roughly 340 px wide until Run Proof.
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


“Do not design screens. Design one persistent object that smoothly changes form as Gradient’s state changes.”


This is the implementation rule most likely to preserve the ambient product feel.
