import { useEffect, useReducer, useRef, useState } from 'react';
import { gradientReducer, showcase, stages, type GradientStage } from '../state/gradientMachine';
import GradientLayer, { type LessonCommand } from './GradientLayer';
import LessonArtifacts, { type LessonEvidence } from './LessonArtifacts';
import { buildCurriculum, type EnvEvidence } from './environmentModel';
import LessonContext from './LessonContext';
import TrainingEvidence, { type TrainingEvidenceData } from './TrainingEvidence';

type Proof = { source: 'real' | 'fallback'; claim: string; pre?: { model_id?: string }; tasks: { task_id: string; pre_reward: number; post_reward: number; pre_artifact: string; post_artifact: string; pre_code?: string; post_code?: string }[]; examples?: Record<string, { verifier?: { reward?: number; verifier_reason?: string; duration_ms?: number }; seed?: number; sandbox_image?: string; environment_hash?: string; verified_at?: string; code?: string }> };
export type DemoSnapshot = { current: { pre: { score: { passed: number; total: number } }; training: { status: string; run_id?: string; error?: string }; post: { source: string; status: string }; updated_at: string }; fallback: Proof; proof: Proof | null; lesson?: LessonEvidence; trainingEvidence?: TrainingEvidenceData; evidenceError?: string };

export default function DemoCompanion() {
  const [model, dispatch] = useReducer(gradientReducer, showcase('idle'));
  const [snapshot, setSnapshot] = useState<DemoSnapshot>();
  const [error, setError] = useState<string>();
  const [reading, setReading] = useState(false);
  const [selectedExample, setSelectedExample] = useState(0);
  const [typing, setTyping] = useState(false);
  const readingVersion = useRef(0);
  const resetLesson = () => {
    window.gradientDesktop?.demoAbort?.(); // kill any in-flight takeover typing first
    readingVersion.current++;
    setReading(false);
    setTyping(false);
    setError(undefined);
    setSelectedExample(0);
    dispatch({ type: 'reset' });
    dispatch({ type: 'showcase', stage: 'idle' });
  };
  const readLesson = async () => {
    const version = ++readingVersion.current;
    setReading(true);
    setTyping(false);
    try {
      const data = await window.gradientDesktop!.demoSnapshot();
      if (version !== readingVersion.current) return;
      setSnapshot(data);
      dispatch({ type: 'showcase', stage: 'lesson_candidate' });
    } catch (cause) { if (version === readingVersion.current) setError(String(cause)); }
    finally { if (version === readingVersion.current) setReading(false); }
  };
  useEffect(() => {
    let disposed = false;
    const refresh = async () => {
      try { const data = await window.gradientDesktop!.demoSnapshot(); if (!disposed) { setSnapshot(data); setError(undefined); } }
      catch (cause) { if (!disposed) setError(String(cause)); }
    };
    void refresh();
    const poll = setInterval(() => void refresh(), 2000);
    return () => { disposed = true; clearInterval(poll); };
  }, []);
  useEffect(() => window.gradientDesktop?.onTeach(() => void readLesson()), []);
  useEffect(() => window.gradientDesktop?.onDemoReset?.(() => resetLesson()), []);
  useEffect(() => { window.gradientDesktop?.proof(model.stage === 'proof'); }, [model.stage]);
  const proof = snapshot?.fallback;
  const evidence = snapshot?.trainingEvidence;
  const isEvidence = model.stage === 'proof' && !!evidence;
  const example = isEvidence ? evidence.examples[selectedExample] : undefined;
  const position = stages.indexOf(model.stage);
  const lesson = snapshot?.lesson && {
    ...snapshot.lesson,
    capability: position >= stages.indexOf('builder_working') ? snapshot.lesson.capability : undefined,
    tasks: position >= stages.indexOf('lesson_ready') ? snapshot.lesson.tasks : [],
    primeRun: position >= stages.indexOf('training') ? snapshot.lesson.primeRun : undefined,
  };
  const stepping = ['observer_working', 'builder_working', 'training'].includes(model.stage);
  const stepOnce = () => {
    const next = stages[Math.min(stages.indexOf(model.stage) + 1, stages.length - 1)];
    dispatch({ type: 'showcase', stage: next });
  };
  const task = proof?.tasks.find((item) => item.pre_reward === 0 && item.post_reward === 1) || proof?.tasks[0];
  const envEvidence: Record<string, EnvEvidence> = {};
  for (const item of proof?.tasks ?? []) {
    envEvidence[item.task_id] = { baselineReward: item.pre_reward, referenceReward: item.post_reward };
  }
  for (const [id, example] of Object.entries(proof?.examples ?? {})) {
    envEvidence[id] = {
      ...envEvidence[id],
      referenceReward: example.verifier?.reward ?? envEvidence[id]?.referenceReward,
      verifierReason: example.verifier?.verifier_reason,
      durationMs: example.verifier?.duration_ms,
      seed: example.seed, sandboxImage: example.sandbox_image,
      envHash: example.environment_hash, verifiedAt: example.verified_at,
      referenceCode: example.code,
    };
  }
  const fullTasks = snapshot?.lesson?.tasks ?? [];
  const curriculum = snapshot?.lesson ? buildCurriculum(
    fullTasks, envEvidence,
    position >= stages.indexOf('builder_working') ? snapshot.lesson.capability?.description || snapshot.lesson.capability?.name : undefined,
    proof?.pre?.model_id, snapshot.lesson.primeRun,
  ) : undefined;
  const command = (action: LessonCommand) => {
    const next: Record<LessonCommand, GradientStage> = { confirm: 'observer_working', dismiss: 'idle', train: 'training', proof: 'proof' };
    dispatch({ type: 'showcase', stage: next[action] });
  };
  const advance = () => {
    if (reading) return;
    if (model.stage === 'idle') { void readLesson(); return; }
    if (model.stage === 'lesson_candidate') { dispatch({ type: 'open' }); return; }
    if (model.stage === 'proof') { dispatch({ type: 'close_proof' }); return; }
    // Stepping stages directly keeps the presenter on one key; canonical buttons stay for mouse users.
    const stepped: Partial<Record<GradientStage, GradientStage>> = { observer_working: 'builder_working', builder_working: 'lesson_ready', training: 'learned' };
    if (stepped[model.stage]) { dispatch({ type: 'showcase', stage: stepped[model.stage]! }); return; }
    const action: Partial<Record<GradientStage, LessonCommand>> = { lesson_open: 'confirm', lesson_ready: 'train', learned: 'proof' };
    const commandForStage = action[model.stage];
    if (commandForStage) command(commandForStage);
  };
  const displayed = {
    ...model, primeRun: undefined, progress: undefined, error: undefined, artifacts: undefined,
    tasks: lesson?.tasks || [], totalTasks: snapshot?.lesson?.tasks?.length,
    trainCount: snapshot?.lesson?.tasks?.filter((item) => item.split === 'train').length,
    unseenCount: snapshot?.lesson?.tasks?.filter((item) => item.split === 'heldout').length,
    stage: model.stage,
    baseline: proof?.tasks.map((item) => ({ task_id: item.task_id, reward: item.pre_reward })) || [],
    trained: proof?.tasks.map((item) => ({ task_id: item.task_id, reward: item.post_reward })) || [],
    comparison: example ? {
      base: example.pre,
      trained: { task_id: example.task_id, reward: example.replay_reward, code: example.code, verifier_reason: `Independent replay: ${example.replay_verifier}` },
    } : task ? {
      base: { task_id: task.task_id, reward: task.pre_reward, code: task.pre_code || task.pre_artifact, verifier_reason: 'Base model result' },
      trained: { task_id: task.task_id, reward: task.post_reward, code: task.post_code || task.post_artifact, verifier_reason: 'Verified reference solution' },
    } : {},
    events: [{ type: 'demo_source', source: 'fallback', claim: proof?.claim, status: snapshot?.current }],
  };
  return <main onContextMenu={(event) => { event.preventDefault(); window.gradientDesktop?.menu(); }}
    onKeyDown={(event) => {
      const target = event.target as HTMLElement | null;
      if (event.ctrlKey || event.metaKey || event.altKey) return;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) return;
      if (event.key === 'n' || event.key === 'N' || event.key === 'ArrowRight') { event.preventDefault(); advance(); }
    }}>
    <GradientLayer model={displayed} dispatch={dispatch} command={command} inspect={async () => {}} curriculum={curriculum}
      nextBeat={stepping ? { label: 'Continue →', onNext: stepOnce } : undefined}
      onAnchor={(event) => {
        if (event.shiftKey || model.stage !== 'idle' || typing) return;
        window.gradientDesktop?.demoType?.();
        setTyping(true);
        return true;
      }}
      activity={reading ? <><p role="status">Looking for a lesson…</p><LessonContext context={snapshot?.lesson?.context} reading /></> : undefined}
      connectionDetails={<>{lesson && <LessonArtifacts lesson={lesson} />}
      <div className="demo-footer">
        <div className="demo-switch"><button className="text-button" onClick={resetLesson} title="Return to the start of the demo lesson">Reset</button></div>
        {error && <p role="alert">{error}</p>}
        {snapshot?.evidenceError && <details><summary>Training evidence unavailable</summary><p>{snapshot.evidenceError}</p></details>}
        {stepping && <button className="text-button" onClick={stepOnce}>Continue lesson</button>}
        {['idle'].includes(model.stage) && <button className="text-button" onClick={() => void readLesson()}>Teach lesson</button>}
        <p className="muted">Click the sprite once to start · Lesson found follows the correction · Continue moves each step</p>
      </div></>}
      proofContext={isEvidence ? {
        title: 'Training evidence', subtitle: 'Selected Qwen training rollouts', trainedLabel: 'Qwen during training',
        footer: 'Recorded model outputs · Original task and verifier · Independent Docker replay', playback: true,
        content: <TrainingEvidence evidence={evidence} selected={selectedExample} select={setSelectedExample} />,
      } : { title: 'Task comparison', subtitle: 'Base model and reference solution', trainedLabel: 'Reference solution', footer: 'Reference solutions are hand-authored and verified separately from model training.', reference: true, playback: true }} />
  </main>;
}
