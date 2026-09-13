import { useEffect, useRef, useState, type ReactNode } from 'react';
import { animate, motion, useReducedMotion } from 'motion/react';
import type { Result } from '../state/gradientMachine';
import { codePlayback, timing } from '../motion/springs';

function ResultView({ result, title, playback = false, delay = 0 }: { result?: Result; title: string; playback?: boolean; delay?: number }) {
  const reducedMotion = useReducedMotion();
  const code = result?.code || '';
  const [visible, setVisible] = useState(0);
  const [finished, setFinished] = useState(false);
  const output = useRef<HTMLPreElement>(null);
  const replay = playback && !reducedMotion && !!code;
  useEffect(() => {
    if (!replay) return;
    setVisible(0);
    setFinished(false);
    const duration = Math.min(codePlayback.maximum, Math.max(codePlayback.minimum, code.length / codePlayback.charactersPerSecond));
    const end = code.length * (1 + codePlayback.verdictPause / duration);
    const animation = animate(0, end, { duration: duration + codePlayback.verdictPause, delay, ease: 'linear',
      onUpdate: (value) => setVisible(Math.min(code.length, Math.floor(value))), onComplete: () => setFinished(true) });
    return () => animation.stop();
  }, [code, replay, delay]);
  useEffect(() => { if (replay && output.current) output.current.scrollTop = output.current.scrollHeight; }, [visible, replay]);
  const complete = !replay || finished;
  return <section className="proof-result" aria-busy={!complete}><h3>{title}</h3><pre ref={output}>{code ? replay ? code.slice(0, visible) : code : 'Waiting for the result…'}{!complete && <span className="code-cursor" aria-hidden="true">▍</span>}</pre>{result && complete && <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reducedMotion ? 0 : timing.fast }}><strong className={result.reward === 1 ? 'pass' : 'fail'}>{result.reward === 1 ? '✓ PASS' : '× FAIL'}</strong><p>{result.verifier_reason}</p></motion.div>}</section>;
}
export function BaseResult({ result }: { result?: Result }) { return <ResultView title="BASE QWEN" result={result} />; }
export function TrainedResult({ result }: { result?: Result }) { return <ResultView title="GRADIENT QWEN" result={result} />; }
export function ProofFooter() { return <footer>Same model · Same task · Same verifier<span>Different weights</span></footer>; }
export type ProofContext = { title: string; subtitle: string; trainedLabel: string; footer: string; reference?: boolean; playback?: boolean; content?: ReactNode };
export default function ProofDrawer({ results, close, error, context }: { results: Partial<Record<'base' | 'trained', Result>>; close: () => void; error?: string; context?: ProofContext }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [skipPlayback, setSkipPlayback] = useState(false);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    dialog.current?.showModal();
    return () => { dialog.current?.close(); previous?.focus(); };
  }, []);
  return <motion.dialog ref={dialog} className={`proof-drawer ${context?.content ? 'training-evidence' : ''}`} aria-labelledby="proof-title" onCancel={(event) => { event.preventDefault(); close(); }} initial={{ y: '100%', opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: '100%', opacity: 0 }} transition={{ duration: timing.normal }}>
    <button className="close-button" aria-label="Close proof" onClick={close} autoFocus>×</button><h2 id="proof-title">{context?.title || 'UNSEEN TASK'}</h2><p className="muted">{context?.subtitle || 'Frozen before training'}</p>{context?.content}{context?.playback && !skipPlayback && <button className="text-button" onClick={() => setSkipPlayback(true)}>Show full results</button>}{error && <p role="alert">Proof could not finish. {error}</p>}<div className="proof-columns"><ResultView key={`base:${results.base?.task_id}`} title="BASE QWEN" result={results.base} playback={context?.playback && !skipPlayback} /><ResultView key={`trained:${results.trained?.task_id}`} title={context?.trainedLabel || 'GRADIENT QWEN'} result={results.trained} playback={context?.playback && !skipPlayback} delay={codePlayback.stagger} /></div>{context ? <footer>{context.footer}</footer> : <ProofFooter />}
  </motion.dialog>;
}
