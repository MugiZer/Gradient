import { useEffect, useReducer, useRef, useState } from 'react';
import { gradientReducer, initialGradient } from '../state/gradientMachine';
import useGradientEvents, { request } from '../state/useGradientEvents';
import GradientLayer from './GradientLayer';
import DemoCompanion, { type DemoSnapshot } from './DemoCompanion';
import ModeControls from './ModeControls';
import LessonContext, { type ConversationContext } from './LessonContext';
import '../styles/desktop.css';

type Connection = { session_id: string | null; connected: boolean; error?: string; last_message_at?: string };
declare global {
  interface Window {
    gradientDesktop?: { pointer: (interactive: boolean) => void; proof: (expanded: boolean) => void; menu: () => void; mode: (mode: 'live' | 'experiment' | 'fallback') => void; onTeach: (callback: () => void) => () => void; onMode: (callback: (mode: 'live' | 'experiment' | 'fallback') => void) => () => void; demoSnapshot: () => Promise<DemoSnapshot> };
  }
}

export default function DesktopCompanion() {
  const [model, dispatch] = useReducer(gradientReducer, initialGradient);
  const [mode, setMode] = useState<'live' | 'experiment' | 'fallback'>('live');
  useEffect(() => window.gradientDesktop?.onMode((value) => { setMode(value); setNotice(undefined); setObservation(undefined); setBusy(false); requesting.current = false; generation.current++; }), []);
  const [connection, setConnection] = useState<Connection>({ session_id: null, connected: false });
  const live = useGradientEvents(dispatch, mode !== 'live', connection.session_id || '');
  const [observation, setObservation] = useState<string>();
  const [notice, setNotice] = useState<string>();
  const requesting = useRef(false);
  const generation = useRef(0);
  const [busy, setBusy] = useState(false);
  const [context, setContext] = useState<ConversationContext>();

  async function observeLesson() {
    if (requesting.current) return;
    requesting.current = true;
    const attempt = ++generation.current;
    setBusy(true);
    setContext(undefined);
    setNotice('Looking for a lesson…');
    void request<ConversationContext>('/native/context').then((value) => { if (attempt === generation.current) setContext(value || undefined); }).catch(() => {});
    try {
      const result = await request<{ run_id: string; context?: ConversationContext }>('/native/observe', {});
      if (attempt !== generation.current) return;
      if (result.context) setContext(result.context);
      setObservation(result.run_id);
    } catch (error) { if (attempt === generation.current) { setNotice(String(error)); requesting.current = false; setBusy(false); } }
  }
  useEffect(() => mode === 'live' ? window.gradientDesktop?.onTeach(() => void observeLesson()) : undefined, [mode]);
  useEffect(() => {
    if (!observation) return;
    let disposed = false;
    const refresh = async () => {
      try {
        const run = await request<{ active: boolean; events: { type: string; state?: string; error?: string }[] }>(`/runs/${encodeURIComponent(observation)}`);
        if (disposed) return;
        const failed = [...run.events].reverse().find((event) => event.state === 'FAILED' || event.state === 'INTERRUPTED');
        const candidate = run.events.some((event) => event.type === 'correction_candidate');
        if (run.active && !candidate && !failed) return;
        setNotice(failed?.error || (candidate ? undefined : 'No teachable correction found in the recent conversation.'));
        setObservation(undefined);
        setBusy(false);
        requesting.current = false;
      } catch (error) { if (!disposed) { setNotice(String(error)); setObservation(undefined); requesting.current = false; setBusy(false); } }
    };
    void refresh();
    const poll = window.setInterval(() => void refresh(), 1000);
    return () => { disposed = true; clearInterval(poll); };
  }, [observation]);

  useEffect(() => {
    document.documentElement.classList.add('desktop');
    let disposed = false;
    const refresh = async () => {
      try {
        const status = await request<Connection>('/native');
        if (!disposed) setConnection(status);
      } catch (error) { if (!disposed) setConnection((old) => ({ ...old, connected: false, error: String(error) })); }
    };
    if (mode === 'live') void refresh();
    // Poll real native connection health; lesson work is driven solely by backend events.
    const poll = window.setInterval(() => { if (mode === 'live') void refresh(); }, 2000);
    return () => { disposed = true; clearInterval(poll); document.documentElement.classList.remove('desktop'); };
  }, [mode]);

  useEffect(() => { if (mode === 'live') window.gradientDesktop?.proof(model.stage === 'proof'); }, [model.stage, mode]);
  useEffect(() => {
    let x = -1, y = -1;
    const update = () => {
      const target = document.elementFromPoint(x, y);
      const interactive = !!target?.closest('.gradient-anchor, .lesson-nudge, .agent-tray, .lesson-surface, .peek-surface, .gradient-error, .proof-drawer');
      window.gradientDesktop?.pointer(interactive);
    };
    const pointer = (event: MouseEvent) => { x = event.clientX; y = event.clientY; update(); };
    const leave = () => { x = y = -1; update(); };
    const observer = new MutationObserver(update);
    observer.observe(document.body, { childList: true, subtree: true });
    document.addEventListener('mousemove', pointer);
    document.addEventListener('mouseleave', leave);
    return () => { observer.disconnect(); document.removeEventListener('mousemove', pointer); document.removeEventListener('mouseleave', leave); };
  }, []);

  if (mode !== 'live') return <DemoCompanion key={mode} mode={mode} />;
  return <main className="desktop-companion" aria-label="Gradient desktop companion" onContextMenu={(event) => { event.preventDefault(); window.gradientDesktop?.menu(); }}>
    <ModeControls mode={mode} />
    <GradientLayer model={{ ...model, error: model.error || connection.error || live.error }} dispatch={dispatch}
      activity={notice ? <div className="manual-observation"><p role="status">{notice}</p>{busy && <LessonContext context={context} reading />}{!busy && <div className="actions"><button className="text-button" onClick={() => setNotice(undefined)}>Dismiss</button><button className="text-button" onClick={() => window.gradientDesktop?.mode('fallback')}>Open saved lesson</button></div>}</div> : undefined}
      command={(action) => void live.command(action, model)} inspect={live.inspect}
      connectionDetails={<div className="native-connection">
        <p>{connection.connected ? 'Watching this Codex task' : 'No Codex task connected'}</p>
        <button className="text-button" disabled={!connection.connected || !!observation} onClick={() => void observeLesson()}>Teach lesson</button>
        {connection.session_id ? <p className="muted">{connection.session_id}</p> : <p>Use the Gradient plugin in the task you want to connect.</p>}
        {connection.connected && <button className="text-button" onClick={async () => setConnection(await request<Connection>('/native/disconnect', {}))}>Disconnect task</button>}
        {live.connection === 'disconnected' && <button className="text-button" onClick={live.reconnect}>Reconnect events</button>}
        {window.gradientDesktop && <button className="text-button" onClick={() => window.gradientDesktop?.menu()}>Desktop controls</button>}
      </div>} />
  </main>;
}
