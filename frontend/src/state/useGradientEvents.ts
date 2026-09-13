import { useEffect, useRef, useState, type Dispatch } from 'react';
import type { Action, BackendEvent, GradientModel, TranscriptItem } from './gradientMachine';
import type { LessonCommand } from '../gradient/GradientLayer';

export const apiBase = import.meta.env.DEV ? '/api' : '';
export async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, body === undefined ? {} : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : `Request failed (${response.status}).`);
  return data as T;
}

function transcriptEvent(items: TranscriptItem[], event: BackendEvent): TranscriptItem[] {
  const prefix = event.run_id!;
  const update = (item: TranscriptItem, append = false) => {
    const index = items.findIndex((old) => old.id === item.id);
    if (index < 0) return [...items, item];
    return items.map((old, i) => i === index ? { ...item, text: append ? old.text + item.text : item.text } : old);
  };
  if (event.type === 'worker_message') return update({ id: `${prefix}:user`, kind: 'user', text: String(event.text) });
  if (event.type === 'worker_output') {
    // A completed streamed item is already authoritative; the HTTP fallback is only for older runtimes.
    if (items.some((item) => item.id.startsWith(`${prefix}:agent:`))) return items;
    return update({ id: `${prefix}:output`, kind: 'agent', text: String(event.text) });
  }
  if (event.type !== 'worker_event') return items;
  const params = event.params as Record<string, unknown> | undefined;
  if (!params) return items;
  if (event.method === 'item/agentMessage/delta' && typeof params.delta === 'string') {
    return update({ id: `${prefix}:agent:${params.itemId}`, kind: 'agent', text: params.delta }, true);
  }
  const item = params.item as Record<string, unknown> | undefined;
  if (event.method === 'item/completed' && item) {
    if (item.type === 'agentMessage') return update({ id: `${prefix}:agent:${item.id}`, kind: 'agent', text: String(item.text || '') });
    if (item.type === 'commandExecution') return update({ id: `${prefix}:tool:${item.id}`, kind: 'tool', status: 'completed', text: `${item.command || ''}\n${item.aggregatedOutput || ''}` });
    if (item.type === 'fileChange') return update({ id: `${prefix}:diff:${item.id}`, kind: 'diff', text: JSON.stringify(item.changes, null, 2) });
  }
  return items;
}

export default function useGradientEvents(dispatch: Dispatch<Action>, showcase: boolean, nativeSession?: string) {
  const [connection, setConnection] = useState<'connecting' | 'connected' | 'disconnected'>(showcase ? 'connected' : 'connecting');
  const [items, setItems] = useState<TranscriptItem[]>([]);
  const [workerBusy, setWorkerBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [attempt, setAttempt] = useState(0);
  const sending = useRef(false);
  const busyRuns = useRef(new Set<string>());
  const seen = useRef(new Set<string>());

  useEffect(() => {
    if (showcase) return;
    let disposed = false;
    let syncing = true;
    const buffered: BackendEvent[] = [];
    const scope = nativeSession === undefined ? '' : `?native_session=${encodeURIComponent(nativeSession)}`;
    seen.current.clear();
    busyRuns.current.clear();
    dispatch({ type: 'reset' });
    setItems([]);
    const socket = new WebSocket(`${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}${apiBase}/events${scope}`);
    const apply = (event: BackendEvent) => {
      if (disposed) return;
      if (!event || typeof event.type !== 'string' || !event.run_id) return;
      const key = JSON.stringify(event);
      if (seen.current.has(key)) return;
      seen.current.add(key);
      dispatch({ type: 'event', event });
      setItems((previous) => transcriptEvent(previous, event));
      if (event.type === 'agent_status' && event.agent === 'worker') {
        if (event.status === 'WORKING') busyRuns.current.add(event.run_id);
        else busyRuns.current.delete(event.run_id);
        setWorkerBusy(busyRuns.current.size > 0);
        if (event.status === 'FAILED') setError(String(event.error || 'Codex could not complete the turn.'));
      }
      if (event.type === 'state' && ['FAILED', 'INTERRUPTED'].includes(String(event.state))) {
        busyRuns.current.delete(event.run_id);
        setWorkerBusy(busyRuns.current.size > 0);
      }
    };
    socket.onopen = async () => {
      try {
        const runs = await request<{ run_id: string }[]>(`/runs${scope}`);
        const histories = await Promise.all(runs.map((run) => request<{ events: BackendEvent[]; active: boolean; run_id: string; artifacts: string[] }>(`/runs/${encodeURIComponent(run.run_id)}`)));
        if (disposed) return;
        [...histories.flatMap((run) => run.events), ...buffered].sort((a, b) => String(a.timestamp).localeCompare(String(b.timestamp))).forEach(apply);
        for (const history of histories) dispatch({ type: 'event', event: { type: 'artifacts_available', run_id: history.run_id, paths: history.artifacts } });
        for (const history of histories) if (!history.active) busyRuns.current.delete(history.run_id);
        setWorkerBusy(busyRuns.current.size > 0);
        syncing = false;
        setConnection('connected');
        setError(undefined);
      } catch (cause) {
        if (!disposed) { setError(String(cause)); socket.close(); }
      }
    };
    socket.onmessage = (message) => {
      try {
        const event = JSON.parse(message.data) as BackendEvent;
        if (event.type === 'resync_required') { socket.close(); return; }
        if (syncing) buffered.push(event); else apply(event);
      } catch { setError('An event could not be read. Reconnect to restore the saved history.'); }
    };
    socket.onclose = () => { if (!disposed) setConnection('disconnected'); };
    socket.onerror = () => { if (!disposed) setError('Cannot reach Gradient. Check that the backend is running.'); };
    return () => { disposed = true; socket.close(); };
  }, [dispatch, showcase, attempt, nativeSession]);

  async function inspect(runId: string) {
    if (showcase) return;
    try {
      const data = await request<{ artifacts: string[] }>(`/runs/${encodeURIComponent(runId)}`);
      dispatch({ type: 'event', event: { type: 'artifacts_available', run_id: runId, paths: data.artifacts } });
    } catch (cause) { dispatch({ type: 'error', message: String(cause) }); }
  }

  async function send(message: string) {
    if (sending.current || workerBusy || connection !== 'connected' || showcase) return false;
    sending.current = true;
    setWorkerBusy(true);
    setError(undefined);
    try {
      await request('/interactions', {
        human_message: message, original_task: items.find((item) => item.kind === 'user')?.text || message,
        bad_agent_output: [...items].reverse().find((item) => item.kind === 'agent')?.text.slice(0, 32000) || '',
      });
      return true;
    } catch (cause) { setError(String(cause)); setWorkerBusy(false); return false; }
    finally { sending.current = false; }
  }
  async function command(action: LessonCommand, model: GradientModel) {
    if (!model.runId || model.pending) return;
    dispatch({ type: 'pending', operation: action });
    try {
      const root = `/runs/${encodeURIComponent(model.runId)}`;
      const task = model.tasks.find((item) => item.split === 'heldout')?.id;
      if (action === 'proof' && !task) throw new Error('No frozen unseen task is available for this lesson.');
      const path = action === 'train' ? `${root}/training/launch` : action === 'proof' ? `${root}/compare/${encodeURIComponent(task!)}` : `${root}/${action}`;
      await request(path, {});
      dispatch({ type: 'pending' });
    } catch (cause) { dispatch({ type: 'error', message: String(cause) }); }
  }
  return { connection, items, workerBusy, error, send, command, inspect, reconnect: () => { setConnection('connecting'); setAttempt((n) => n + 1); } };
}
