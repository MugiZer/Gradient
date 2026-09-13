import { useReducer } from 'react';
import { gradientReducer, initialGradient, stages, type GradientStage, type TranscriptItem } from '../state/gradientMachine';
import useGradientEvents from '../state/useGradientEvents';
import GradientLayer, { type LessonCommand } from '../gradient/GradientLayer';
import CodexTranscript from './CodexTranscript';
import Composer from './Composer';

const exampleTranscript: TranscriptItem[] = [
  { id: 'example-user', kind: 'user', text: 'Add a regression test proving another process can read the saved snapshot.' },
  { id: 'example-agent', kind: 'agent', text: 'I’ll check the save path and the existing tests, then add a regression test for the persisted result.' },
  { id: 'example-tool', kind: 'tool', text: 'Example tool output for visual inspection only.', status: 'completed' },
  { id: 'example-diff', kind: 'diff', text: 'Example diff preview for visual inspection only.' },
  { id: 'example-correction', kind: 'user', text: 'The test only checks the returned object. Have a fresh process read the file and assert what it sees.' },
];
export default function CodexWorkspace({ showcase = false }: { showcase?: boolean }) {
  const [model, dispatch] = useReducer(gradientReducer, initialGradient);
  const live = useGradientEvents(dispatch, showcase);
  const command = (action: LessonCommand) => {
    if (!showcase) { void live.command(action, model); return; }
    const next: Record<LessonCommand, GradientStage> = { confirm: 'observer_working', dismiss: 'idle', train: 'training', proof: 'proof' };
    dispatch({ type: 'showcase', stage: next[action] });
  };
  return <main className="codex-workspace">
    <header className="workspace-header"><div className="workspace-brand">Codex<span>Workspace</span></div><div className="connection" data-connected={live.connection === 'connected'}>{showcase ? 'UI showcase' : live.connection === 'connected' ? 'Connected' : live.connection === 'connecting' ? 'Connecting' : 'Disconnected'}{live.connection === 'disconnected' && <button className="text-button" onClick={live.reconnect}>Reconnect</button>}</div></header>
    {showcase && <nav className="showcase-controls" aria-label="UI states"><p>Developer showcase · Illustrative data · No backend actions</p>{stages.map((stage) => <button key={stage} aria-pressed={model.stage === stage} onClick={() => dispatch({ type: 'showcase', stage })}>{stage}</button>)}</nav>}
    <CodexTranscript items={showcase ? exampleTranscript : live.items} busy={live.workerBusy} />
    {live.error && <p className="connection-error" role="alert">{live.error}</p>}
    <Composer disabled={showcase || live.workerBusy || live.connection !== 'connected'} send={live.send} />
    <GradientLayer model={model} dispatch={dispatch} command={command} inspect={live.inspect} />
  </main>;
}
