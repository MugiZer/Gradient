import { useEffect, useRef } from 'react';
import type { TranscriptItem } from '../state/gradientMachine';
import ToolAction from './ToolAction';
import DiffPreview from './DiffPreview';

export function UserTurn({ text }: { text: string }) {
  return <article className="turn user-turn"><span className="turn-label">You</span><div>{text}</div></article>;
}
export function AgentTurn({ text }: { text: string }) {
  return <article className="turn agent-turn"><span className="turn-label">Codex</span><div>{text}</div></article>;
}
export default function CodexTranscript({ items, busy }: { items: TranscriptItem[]; busy: boolean }) {
  const view = useRef<HTMLDivElement>(null);
  const follow = useRef(true);
  useEffect(() => { if (follow.current && view.current) view.current.scrollTop = view.current.scrollHeight; }, [items, busy]);
  return <div className="transcript" ref={view} onScroll={() => {
    const el = view.current!; follow.current = el.scrollHeight - el.scrollTop - el.clientHeight < 100;
  }} role="log" aria-label="Codex conversation" aria-live="polite" aria-relevant="additions text">
    {!items.length && <div className="empty-workspace"><h1>What are we working on?</h1><p>Start a conversation with Codex.</p></div>}
    <div className="transcript-content">{items.map((item) => item.kind === 'user' ? <UserTurn key={item.id} text={item.text} /> : item.kind === 'agent' ? <AgentTurn key={item.id} text={item.text} /> : item.kind === 'diff' ? <DiffPreview key={item.id} text={item.text} /> : <ToolAction key={item.id} text={item.text} status={item.status} />)}
      {busy && <p className="worker-status">Codex is working<span aria-hidden="true"> ···</span></p>}
    </div>
  </div>;
}
