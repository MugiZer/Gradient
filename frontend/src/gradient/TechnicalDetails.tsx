import type { BackendEvent } from '../state/gradientMachine';
import { apiBase, request } from '../state/useGradientEvents';
import { useEffect, useState, type ReactNode } from 'react';
import LessonArtifacts, { type LessonEvidence } from './LessonArtifacts';
export default function TechnicalDetails({ events, artifacts, runId, close, children }: { events: BackendEvent[]; artifacts?: string[]; runId?: string; close: () => void; children?: ReactNode }) {
  const [lesson, setLesson] = useState<LessonEvidence>();
  useEffect(() => {
    if (!runId || !artifacts?.length) return;
    let disposed = false;
    const read = async <T,>(path: string): Promise<T | undefined> => artifacts.includes(path) ? request<T>(`/runs/${encodeURIComponent(runId)}/artifacts/${path}`).catch(() => undefined) : undefined;
    void Promise.all([read<LessonEvidence['capability']>('capability.json'), read<LessonEvidence['tasks']>('curriculum/train_specs.json'), read<LessonEvidence['tasks']>('curriculum/heldout_specs.json'), read<LessonEvidence['context']>('interaction.json')]).then(([capability, train, unseen, context]) => {
      if (!disposed) setLesson({ capability, tasks: [...(train || []), ...(unseen || [])], context });
    });
    return () => { disposed = true; };
  }, [runId, artifacts]);
  return <section className="technical-details" aria-label="Technical details">
    <button className="close-button" aria-label="Close technical details" onClick={close}>×</button><h2>Technical details</h2>
    {children}
    {lesson && <LessonArtifacts lesson={lesson} />}
    {!!artifacts?.length && <details><summary>Artifacts</summary>{artifacts.map((path) => <a key={path} href={`${apiBase}/runs/${encodeURIComponent(runId!)}/artifacts/${path.split('/').map(encodeURIComponent).join('/')}`} target="_blank" rel="noreferrer">{path}</a>)}</details>}
    {events.length ? <details><summary>Event log</summary><pre>{JSON.stringify(events, null, 2)}</pre></details> : <p>No lesson events yet.</p>}
  </section>;
}
