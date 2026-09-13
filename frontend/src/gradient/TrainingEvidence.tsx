import type { Result } from '../state/gradientMachine';

export type TrainingEvidenceData = {
  captured_at: string; model: string; prime_run_id: string; claim: string; scope: string; selection: string;
  status: string; latest_step: number; max_steps: number;
  examples: { task_id: string; function: string; pre_reward: number; training_reward: number; step: number;
    sample_id: number; policy_version: number; replay_reward: number; replay_verifier: string; code: string;
    source_sha256: string; prime_sample: string; pre: Result; replay: Result & { duration_ms: number; seed: number } }[];
};

export default function TrainingEvidence({ evidence, selected, select }: { evidence: TrainingEvidenceData; selected: number; select: (index: number) => void }) {
  const sample = evidence.examples[selected];
  return <div className="training-evidence-content">
    <p>{evidence.claim}</p><p className="muted">{evidence.scope}</p>
    <div className="evidence-examples" role="group" aria-label="Training examples">{evidence.examples.map((item, index) => <button className="text-button" key={item.task_id} aria-pressed={index === selected} onClick={() => select(index)}>{item.function}</button>)}</div>
    <p className="muted">Step {sample.step} · Sample {sample.sample_id} · Policy version {sample.policy_version}</p>
    <details><summary>Independent verification</summary><p>{sample.replay.verifier_reason} · Reward {sample.replay.reward} · {sample.replay.duration_ms} ms</p><p>Original task seed: {sample.replay.seed}</p><a href={`/evidence/${sample.task_id}_replay.json`} target="_blank" rel="noreferrer">Open verifier result ↗</a></details>
    <details><summary>Source and selection</summary><p>{evidence.selection}</p><p>Captured {new Date(evidence.captured_at).toLocaleString()} · {evidence.status} · Step {evidence.latest_step} of {evidence.max_steps} at capture</p><p>Source SHA256: <code>{sample.source_sha256}</code></p><a href={`/evidence/${sample.prime_sample}`} target="_blank" rel="noreferrer">Open Prime sample ↗</a></details>
    <nav className="evidence-downloads" aria-label="Evidence files">
      <a href="/evidence/gradient_training_evidence.png" target="_blank" rel="noreferrer">Evidence card</a>
      <a href="/evidence/gradient_training_evidence.pdf" target="_blank" rel="noreferrer">PDF</a>
      <a href="/evidence/gradient_training_evidence_bundle.zip" download>Raw evidence ZIP</a>
      <a href={`https://app.primeintellect.ai/dashboard/training/${encodeURIComponent(evidence.prime_run_id)}`} target="_blank" rel="noreferrer">Prime run ↗</a>
    </nav>
  </div>;
}
