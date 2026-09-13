export const stages = ['idle', 'lesson_candidate', 'lesson_open', 'observer_working', 'builder_working', 'lesson_ready', 'training', 'learned', 'proof'] as const;
export type GradientStage = typeof stages[number];
export type AgentRole = 'gradient' | 'observer' | 'builder';
export type AgentState = 'idle' | 'noticing' | 'thinking' | 'working' | 'done' | 'attention';
export type BackendEvent = { type: string; run_id?: string; timestamp?: string; [key: string]: unknown };
export type Result = { task_id: string; reward: number; code?: string; verifier_reason?: string };
export type TranscriptItem = { id: string; kind: 'user' | 'agent' | 'tool' | 'diff'; text: string; status?: string };
export type GradientModel = {
  stage: GradientStage; runId?: string; title: string; events: BackendEvent[];
  tasks: { id: string; split: string }[]; trainCount?: number; unseenCount?: number;
  totalTasks?: number;
  primeRun?: string; progress?: number;
  baseline: Result[]; trained: Result[]; comparison: Partial<Record<'base' | 'trained', Result>>;
  proofTask?: string; error?: string; pending?: string;
  peek?: 'observer' | 'builder' | 'details';
  artifacts?: string[];
  disclosure?: 'open' | 'closed';
};
export const initialGradient: GradientModel = {
  stage: 'idle', title: 'Observable Effect vs Simulation', events: [], tasks: [],
  baseline: [], trained: [], comparison: {},
};
export type Action =
  | { type: 'reset' }
  | { type: 'event'; event: BackendEvent }
  | { type: 'open' | 'dismiss' | 'close_proof' | 'clear_error' | 'toggle_disclosure' }
  | { type: 'peek'; peek?: GradientModel['peek'] }
  | { type: 'pending'; operation?: string }
  | { type: 'error'; message: string }
  | { type: 'showcase'; stage: GradientStage };

const eventStages: Record<string, GradientStage> = {
  correction_candidate: 'lesson_candidate', lesson_confirmed: 'observer_working',
  capability_extracted: 'builder_working', curriculum_compiled: 'lesson_ready',
  training_started: 'training', training_completed: 'learned', proof_started: 'proof',
};
const legacyStages: Record<string, GradientStage> = {
  ENVIRONMENTS_COMPILED: 'lesson_ready', TRAINED: 'learned',
};
const record = (value: unknown): Record<string, unknown> => value && typeof value === 'object' ? value as Record<string, unknown> : {};
const upsert = (items: Result[], result: Result) => [...items.filter((item) => item.task_id !== result.task_id), result];

export function gradientReducer(state: GradientModel, action: Action): GradientModel {
  switch (action.type) {
    case 'reset': return initialGradient;
    case 'open': return state.stage === 'lesson_candidate' ? { ...state, stage: 'lesson_open', disclosure: 'open' } : state;
    case 'toggle_disclosure': return { ...state, disclosure: state.disclosure === 'closed' ? 'open' : 'closed', peek: undefined };
    case 'dismiss': return ['lesson_candidate', 'lesson_open'].includes(state.stage) ? { ...state, stage: 'idle', peek: undefined } : state;
    case 'close_proof': return { ...state, stage: 'learned' };
    case 'peek': return { ...state, peek: action.peek };
    case 'pending': return { ...state, pending: action.operation, error: action.operation ? undefined : state.error };
    case 'error': return { ...state, error: action.message, pending: undefined };
    case 'clear_error': return { ...state, error: undefined };
    case 'showcase': return showcase(action.stage);
    case 'event': break;
  }
  const event = action.event;
  if (!event.run_id || event.type === 'heartbeat') return state;
  if (event.type.startsWith('worker_') || (event.type === 'agent_status' && event.agent === 'worker')) return state;
  const candidate = event.type === 'correction_candidate' || event.type === 'learning_event_detected';
  if (state.runId && state.runId !== event.run_id && !candidate) return state;
  // A new lesson replaces the previous ambient object; each run retains its own evidence on disk.
  const current = candidate && event.run_id !== state.runId ? initialGradient : state;
  let next = { ...current, runId: event.run_id, events: [...current.events, event] };
  if (eventStages[event.type]) next = { ...next, stage: eventStages[event.type], pending: undefined, peek: undefined, error: undefined, disclosure: 'open' };
  if (event.type === 'learning_event_detected') next.stage = 'lesson_candidate';
  if (event.type === 'state') {
    const backendStage = String(event.state);
    if (legacyStages[backendStage]) next.stage = legacyStages[backendStage];
    if (['FAILED', 'INTERRUPTED'].includes(backendStage)) {
      next.error = typeof event.error === 'string' ? event.error : 'Work was interrupted.';
      next.pending = undefined;
    }
  }
  if (event.type === 'lesson_dismissed') next.stage = 'idle';
  if (event.type === 'artifacts_available' && Array.isArray(event.paths)) next.artifacts = event.paths.filter((path): path is string => typeof path === 'string');
  if (typeof event.title === 'string') next.title = event.title;
  if (event.type === 'task_spec_created') {
    if (typeof event.total === 'number') next.totalTasks = event.total;
    const task = record(event.task);
    if (typeof task.id === 'string' && typeof task.split === 'string') {
      next.tasks = [...next.tasks.filter((t) => t.id !== task.id), { id: task.id, split: task.split }];
    }
  }
  if (['curriculum_compiled', 'environments_compiled'].includes(event.type)) {
    next.stage = 'lesson_ready';
    next.trainCount = typeof event.train_count === 'number' ? event.train_count : next.tasks.filter((t) => t.split === 'train').length;
    next.unseenCount = typeof event.unseen_count === 'number' ? event.unseen_count : next.tasks.filter((t) => t.split === 'heldout').length;
  }
  if (event.type === 'training_started') {
    const run = record(event.run);
    if (typeof run.id === 'string') next.primeRun = run.id;
  }
  if (event.type === 'training_progress' && typeof event.progress === 'number') next.progress = Math.max(0, Math.min(1, event.progress));
  if (event.type === 'training_result') next.stage = 'learned';
  if (['baseline_result', 'heldout_result'].includes(event.type) && event.split === 'heldout' && typeof event.task_id === 'string' && (event.reward === 0 || event.reward === 1)) {
    const result = event as unknown as Result;
    if (event.type === 'baseline_result') next.baseline = upsert(next.baseline, result);
    else next.trained = upsert(next.trained, result);
  }
  if (event.type === 'proof_started') {
    next.comparison = {};
    next.proofTask = String(event.task_id);
  }
  if (event.type === 'comparison_result' && (event.label === 'base' || event.label === 'trained') && event.task_id === next.proofTask && (event.reward === 0 || event.reward === 1) && typeof event.code === 'string') {
    next.comparison = { ...next.comparison, [event.label]: event as unknown as Result };
  }
  return next;
}

export function showcase(stage: GradientStage): GradientModel {
  const tasks = Array.from({ length: 12 }, (_, i) => ({ id: `example_${i}`, split: i < 8 ? 'train' : 'heldout' }));
  const results = Array.from({ length: 5 }, (_, i) => ({ task_id: `example_${i}`, reward: 1 }));
  return {
    ...initialGradient, stage, runId: 'showcase', tasks: stage === 'builder_working' ? tasks.slice(0, 6) : tasks, totalTasks: 12, trainCount: 8, unseenCount: 4,
    primeRun: 'example', progress: 0.6, baseline: results.map((r, i) => ({ ...r, reward: i === 0 ? 1 : 0 })), trained: results,
    comparison: {
      base: { task_id: 'example', reward: 0, code: 'return {"path": path, "data": data}', verifier_reason: 'No file observed by a fresh reader.' },
      trained: { task_id: 'example', reward: 1, code: 'Path(path).write_text(data, encoding="utf-8")', verifier_reason: 'A fresh reader observed the requested data.' },
    },
    events: [{ type: 'showcase_fixture', title: 'Illustrative design data only' }],
  };
}
