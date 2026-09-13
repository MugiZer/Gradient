import { useEffect, useReducer, useRef, useState } from 'react';
import { gradientReducer, showcase, stages, type GradientStage } from '../state/gradientMachine';
import GradientLayer, { type LessonCommand } from './GradientLayer';
import { formatScore } from '../state/formatScore';
import ModeControls from './ModeControls';
import LessonArtifacts, { type LessonEvidence } from './LessonArtifacts';
import LessonContext from './LessonContext';
import TrainingEvidence, { type TrainingEvidenceData } from './TrainingEvidence';

type Proof = { source: 'real' | 'fallback'; claim: string; tasks: { task_id: string; pre_reward: number; post_reward: number; pre_artifact: string; post_artifact: string; pre_code?: string; post_code?: string }[] };
export type DemoSnapshot = { current: { pre: { score: { passed: number; total: number } }; training: { status: string; run_id?: string; error?: string }; post: { source: string; status: string }; updated_at: string }; fallback: Proof; proof: Proof | null; lesson?: LessonEvidence; trainingEvidence?: TrainingEvidenceData; evidenceError?: string };

export default function DemoCompanion({ mode }: { mode: 'experiment' | 'fallback' }) {
  const [model, dispatch] = useReducer(gradientReducer, showcase(mode === 'fallback' ? 'lesson_candidate' : 'training'));
  const [snapshot, setSnapshot] = useState<DemoSnapshot>();
  const [error, setError] = useState<string>();
  const [reading, setReading] = useState(false);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [selectedExample, setSelectedExample] = useState(0);
  const readingVersion = useRef(0);
  const resetLesson = () => {
    readingVersion.current++;
    setReading(false);
    setError(undefined);
    setEvidenceOpen(false);
    setSelectedExample(0);
    dispatch({ type: 'reset' });
  };
  const readLesson = async () => {
    const version = ++readingVersion.current;
    setReading(true);
    try {
      const data = await window.gradientDesktop!.demoSnapshot();
      if (version !== readingVersion.current) return;
      setSnapshot(data);
      dispatch({ type: 'showcase', stage: 'lesson_open' });
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
  useEffect(() => mode === 'fallback' ? window.gradientDesktop?.onTeach(() => void readLesson()) : undefined, [mode]);
  useEffect(() => { window.gradientDesktop?.proof(model.stage === 'proof'); }, [model.stage]);
  useEffect(() => {
    if (mode === 'experiment' && snapshot?.proof && model.stage === 'training') dispatch({ type: 'showcase', stage: 'learned' });
  }, [snapshot, mode, model.stage]);
  const proof = mode === 'fallback' ? snapshot?.fallback : snapshot?.proof;
  const evidence = snapshot?.trainingEvidence;
  const isEvidence = evidenceOpen && model.stage === 'proof' && !!evidence;
  const example = isEvidence ? evidence.examples[selectedExample] : undefined;
  const position = stages.indexOf(model.stage);
  const lesson = snapshot?.lesson && {
    ...snapshot.lesson,
    capability: position >= stages.indexOf('builder_working') ? snapshot.lesson.capability : undefined,
    tasks: position >= stages.indexOf('lesson_ready') ? snapshot.lesson.tasks : [],
    primeRun: position >= stages.indexOf('training') ? snapshot.lesson.primeRun : undefined,
  };
  const task = proof?.tasks.find((item) => item.pre_reward === 0 && item.post_reward === 1) || proof?.tasks[0];
  const command = (action: LessonCommand) => {
    if (mode === 'experiment' && action !== 'proof') return;
    if (action === 'proof') setEvidenceOpen(false);
    const next: Record<LessonCommand, GradientStage> = { confirm: 'observer_working', dismiss: 'idle', train: 'training', proof: 'proof' };
    dispatch({ type: 'showcase', stage: next[action] });
  };
  const displayed = {
    ...model, primeRun: mode === 'experiment' ? snapshot?.current.training.run_id : undefined, progress: undefined, error: undefined, artifacts: undefined,
    tasks: lesson?.tasks || [], totalTasks: snapshot?.lesson?.tasks?.length,
    trainCount: snapshot?.lesson?.tasks?.filter((item) => item.split === 'train').length,
    unseenCount: snapshot?.lesson?.tasks?.filter((item) => item.split === 'heldout').length,
    stage: mode === 'experiment' && !proof && model.stage !== 'proof' && ['failed', 'unavailable'].includes(snapshot?.current.training.status || '') ? 'idle' as const : model.stage,
    baseline: proof?.tasks.map((item) => ({ task_id: item.task_id, reward: item.pre_reward })) || [],
    trained: proof?.tasks.map((item) => ({ task_id: item.task_id, reward: item.post_reward })) || [],
    comparison: example ? {
      base: example.pre,
      trained: { task_id: example.task_id, reward: example.replay_reward, code: example.code, verifier_reason: `Independent replay: ${example.replay_verifier}` },
    } : task ? {
      base: { task_id: task.task_id, reward: task.pre_reward, code: task.pre_code || task.pre_artifact, verifier_reason: 'Base model result' },
      trained: { task_id: task.task_id, reward: task.post_reward, code: task.post_code || task.post_artifact, verifier_reason: mode === 'fallback' ? 'Verified reference solution' : 'Trained model result' },
    } : {},
    events: [{ type: 'demo_source', source: mode === 'fallback' ? 'fallback' : 'real', claim: proof?.claim, status: snapshot?.current }],
  };
  return <main onContextMenu={(event) => { event.preventDefault(); window.gradientDesktop?.menu(); }}>
    <ModeControls mode={mode} reset={mode === 'fallback' ? resetLesson : undefined} />
    <section className="demo-controls lesson-surface">
      {mode === 'fallback' && <p>{isEvidence ? 'Archived training evidence' : 'Reference solutions'}</p>}
      {mode === 'experiment' && <p>Base pass rate: {formatScore(snapshot?.current.pre.score.passed, snapshot?.current.pre.score.total)} · Training: {snapshot?.current.training.status || 'Loading…'} · Evaluation: {snapshot?.current.post.status || 'Waiting'}</p>}
      {error && <p role="alert">{error}</p>}
      {evidence && position >= stages.indexOf('training') && <button className="text-button" onClick={() => { setEvidenceOpen(true); dispatch({ type: 'showcase', stage: 'proof' }); }}>Training evidence</button>}
      {snapshot?.evidenceError && <details><summary>Training evidence unavailable</summary><p>{snapshot.evidenceError}</p></details>}
      {mode === 'experiment' && snapshot?.current.training.error && <details><summary>Backend status</summary><p>{snapshot.current.training.error}</p></details>}
      {mode === 'fallback' && <>{['observer_working', 'builder_working', 'training'].includes(model.stage) && <button className="text-button" onClick={() => dispatch({ type: 'showcase', stage: stages[Math.min(stages.indexOf(model.stage) + 1, stages.length - 1)] })}>Continue lesson</button>}{['idle', 'learned'].includes(model.stage) && <button className="text-button" onClick={() => void readLesson()}>Teach lesson</button>}</>}
    </section>
    <GradientLayer model={displayed} dispatch={dispatch} command={command} inspect={async () => {}}
      activity={reading ? <><p role="status">Looking for a lesson…</p><LessonContext context={snapshot?.lesson?.context} reading /></> : undefined}
      connectionDetails={lesson && <LessonArtifacts lesson={lesson} />}
      proofContext={isEvidence ? {
        title: 'Training evidence', subtitle: 'Selected Qwen training rollouts', trainedLabel: 'Qwen during training',
        footer: 'Recorded model outputs · Original task and verifier · Independent Docker replay', playback: true,
        content: <TrainingEvidence evidence={evidence} selected={selectedExample} select={setSelectedExample} />,
      } : { title: 'Task comparison', subtitle: mode === 'fallback' ? 'Base model and reference solution' : 'Recorded results on training tasks', trainedLabel: mode === 'fallback' ? 'Reference solution' : 'Gradient Qwen', footer: mode === 'fallback' ? 'Reference solutions are hand-authored and verified separately from model training.' : 'Same training tasks · Same verifier', reference: mode === 'fallback', playback: true }} />
  </main>;
}
