import type { Result } from '../state/gradientMachine';
import { formatScore } from '../state/formatScore';
export default function LearnedArtifact({ title, base, trained, proof, pending, details, reference = false }: { title: string; base: Result[]; trained: Result[]; proof: () => void; pending: boolean; details: () => void; reference?: boolean }) {
  const score = (results: Result[]) => formatScore(results.filter((r) => r.reward === 1).length, results.length);
  return <section aria-label={reference ? 'Reference results' : 'Lesson learned'}><p className="eyebrow">{reference ? 'Reference results' : '✦ Lesson learned'}</p><h2>{title}</h2><dl className="scores" aria-label="Pass rate"><div><dt>Base</dt><dd>{score(base)}</dd></div><div><dt>{reference ? 'Reference' : 'Gradient'}</dt><dd>{score(trained)}</dd></div></dl><button className="primary" onClick={proof} disabled={pending}>{pending ? 'Starting…' : 'Run proof'}</button><button className="text-button details-link" onClick={details}>View details →</button></section>;
}
