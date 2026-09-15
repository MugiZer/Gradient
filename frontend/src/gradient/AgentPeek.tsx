import CurriculumExplorer from './Environments';
import type { Curriculum } from './environmentModel';

export default function AgentPeek({ role, title, complete, total, done, curriculum, details, close }: { role: 'observer' | 'builder'; title: string; complete: number; total?: number; done: boolean; curriculum?: Curriculum; details: () => void; close: () => void }) {
  return <section className="agent-peek" aria-label={`${role} details`}><button className="close-button" aria-label="Close agent peek" onClick={close}>×</button><h2>{role === 'observer' ? 'Observer' : 'Environment Builder'}</h2><p>{role === 'observer' ? done ? 'What you taught:' : 'Understanding what you taught' : 'Creating executable lessons'}</p>{role === 'observer' ? <p>{title}</p> : curriculum && curriculum.total > 0 ? <CurriculumExplorer curriculum={curriculum} /> : complete > 0 ? <p>{complete}{total ? ` / ${total}` : ''} complete</p> : null}<button className="text-button" onClick={details}>View details →</button></section>;
}
