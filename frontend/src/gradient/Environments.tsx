import { useState, type ReactNode } from 'react';
import {
  isolatesOf, objectiveOf, verifierIntentOf, REWARD_RULE,
  type Curriculum, type EnvView,
} from './environmentModel';
import { formatScore } from '../state/formatScore';

const shortHash = (hash?: string) => (hash ? hash.replace(/^sha256:/, '').slice(0, 12) : undefined);

function RewardLine({ env }: { env: EnvView }) {
  const base = env.evidence.baselineReward;
  const ref = env.evidence.referenceReward;
  if (env.heldout) return <p className="muted">Frozen before training · no baseline</p>;
  return <p className="muted">
    Baseline reward: {base === 0 || base === 1 ? base : 'not recorded'}
    {ref === 0 || ref === 1 ? ` · Reference: ${ref}` : ''}
  </p>;
}

function EnvCard({ env, inspect }: { env: EnvView; inspect: () => void }) {
  return <article className="task-artifact env-card">
    <p className="env-card-head">{env.familyLabel} · {env.sideLabel}</p>
    <p><strong>{objectiveOf(env.family, env.side)}</strong></p>
    <p className="muted">{env.functionName} · {env.heldout ? 'held-out' : env.split}{typeof env.difficulty === 'number' ? ` · difficulty ${env.difficulty}` : ''}</p>
    <RewardLine env={env} />
    {typeof env.evidence.durationMs === 'number' && <p className="muted">Verifier {env.evidence.durationMs} ms</p>}
    <button className="text-button" onClick={inspect}>Inspect →</button>
  </article>;
}

function FlowStep({ title, children }: { title: string; children: ReactNode }) {
  return <div className="env-step"><h4>{title}</h4><div>{children}</div></div>;
}

function Inspector({ env, curriculum, back }: { env: EnvView; curriculum: Curriculum; back: () => void }) {
  const evidence = env.evidence;
  const frozen = evidence.verifiedAt ? new Date(evidence.verifiedAt) : undefined;
  return <div>
    <button className="text-button" onClick={back}>← Environments</button>
    <p className="env-card-head">{env.familyLabel} · {env.sideLabel} · {env.heldout ? 'HELD-OUT' : 'TRAIN'}</p>
    <p><strong>{objectiveOf(env.family, env.side)}</strong></p>
    {curriculum.capability && <FlowStep title="Capability"><p className="muted">{curriculum.capability}</p></FlowStep>}
    <FlowStep title="Why this environment exists"><p className="muted">{isolatesOf(env.family, env.side)}</p></FlowStep>
    {env.prompt && <FlowStep title="Task"><p>{env.prompt}</p></FlowStep>}
    <FlowStep title="Initial state"><p className="muted">
      Recorded contract only — no staged world snapshot.
      {env.difficulty !== undefined ? ` Difficulty ${env.difficulty}.` : ''}
      {typeof evidence.seed === 'number' ? ` Seed ${evidence.seed}.` : ''}
      {shortHash(evidence.envHash) ? ` Env ${shortHash(evidence.envHash)}.` : ''}
    </p></FlowStep>
    <FlowStep title="Policy"><p className="muted">
      {curriculum.policyModel || 'Recorded policy'} · tool and step budget not recorded.
    </p></FlowStep>
    <FlowStep title="Resulting state"><p className="muted">
      {evidence.verifierReason || 'No recorded rollout.'}
      {evidence.referenceReward === 0 || evidence.referenceReward === 1 ? ` Reference reward ${evidence.referenceReward}.` : ''}
    </p></FlowStep>
    {evidence.referenceCode && <details><summary>Reference code</summary><pre>{evidence.referenceCode}</pre></details>}
    <FlowStep title="Verifier"><p className="muted">{verifierIntentOf(env.family)}</p>
      <p className="muted">Reward rule: {REWARD_RULE}</p>
      <p className="muted">Gold / no-op / exploit runs not recorded for this lesson.</p>
    </FlowStep>
    <FlowStep title="Reward"><RewardLine env={env} /></FlowStep>
    {env.heldout ? <FlowStep title="Freeze"><p className="muted">
      {frozen && !isNaN(+frozen) ? `Verified ${frozen.toLocaleString()}. ` : ''}Zero training rollouts · verifier artifacts frozen.
      {shortHash(evidence.envHash) ? ` Manifest ${shortHash(evidence.envHash)}.` : ''}
    </p></FlowStep> : <FlowStep title="Calibration"><p className="muted">
      {curriculum.basePass ? `Base pass rate ${formatScore(curriculum.basePass.passed, curriculum.basePass.total)}. ` : 'No baseline rewards recorded. '}
      {curriculum.medianVerifierMs !== undefined ? `Median verifier ${curriculum.medianVerifierMs} ms. ` : ''}
      Rollout counts, flake rate, and failure mix not recorded.
    </p></FlowStep>}
    {!env.heldout && curriculum.referenceReach && <FlowStep title="Training value"><p className="muted">
      Before training: {curriculum.basePass ? formatScore(curriculum.basePass.passed, curriculum.basePass.total) : 'unknown'} ·{' '}
      Reference reach: {formatScore(curriculum.referenceReach.passed, curriculum.referenceReach.total)} (hand-authored reference, not trained weights).
    </p>
    {curriculum.primeRun && <a href={`https://app.primeintellect.ai/dashboard/training/${encodeURIComponent(curriculum.primeRun)}`} target="_blank" rel="noreferrer">Open Prime Intellect ↗</a>}
    </FlowStep>}
  </div>;
}

export default function CurriculumExplorer({ curriculum }: { curriculum: Curriculum }) {
  const [exploring, setExploring] = useState(false);
  const [inspectId, setInspectId] = useState<string>();
  const inspected = inspectId
    ? curriculum.groups.flatMap((g) => [...g.required, ...g.forbidden, ...g.other]).find((e) => e.id === inspectId)
    : undefined;
  if (inspected) return <div className="lesson-artifacts"><Inspector env={inspected} curriculum={curriculum} back={() => setInspectId(undefined)} /></div>;
  if (!exploring) {
    return <div className="lesson-artifacts">
      <p className="env-card-head">Builder · RL environments</p>
      <p className="muted">Capability</p>
      <p>{curriculum.capability || 'Recorded capability'}</p>
      <dl className="scores" aria-label="Environment counts">
        <div><dt>Train</dt><dd>{curriculum.trainRequired + curriculum.trainForbidden} · {curriculum.trainRequired} required · {curriculum.trainForbidden} forbidden</dd></div>
        <div><dt>Held-out</dt><dd>{curriculum.heldout} frozen</dd></div>
      </dl>
      <p className="muted">Coverage</p>
      <p>{curriculum.groups.map((g) => g.label).join(' · ') || 'No environments recorded'}</p>
      <h3>Quality gates</h3>
      <ul className="env-gates">{curriculum.gates.map((gate) => <li key={gate.label}>
        <strong className={gate.pass ? 'pass' : 'fail'}>{gate.pass ? '✓' : '×'} {gate.label}</strong> <span className="muted">— {gate.detail}</span>
      </li>)}</ul>
      {!!curriculum.total && <button className="primary" onClick={() => setExploring(true)}>Explore environments</button>}
    </div>;
  }
  const heldout = curriculum.groups.flatMap((g) => [...g.required, ...g.forbidden, ...g.other]).filter((e) => e.heldout);
  return <div className="lesson-artifacts">
    <button className="text-button" onClick={() => setExploring(false)}>← Summary</button>
    {curriculum.groups.map((group) => {
      const train = (list: EnvView[]) => list.filter((e) => !e.heldout);
      if (!train(group.required).length && !train(group.forbidden).length && !group.other.length) return null;
      return <section key={group.label || 'unlabeled'}>
        <h3>{group.label}</h3>
        {train(group.required).map((env) => <EnvCard key={env.id} env={env} inspect={() => setInspectId(env.id)} />)}
        {!!train(group.required).length && !!train(group.forbidden).length && <p className="muted">↔ boundary pair — the lesson is when to cause the effect, not always or never</p>}
        {train(group.forbidden).map((env) => <EnvCard key={env.id} env={env} inspect={() => setInspectId(env.id)} />)}
        {group.other.map((env) => <EnvCard key={env.id} env={env} inspect={() => setInspectId(env.id)} />)}
      </section>;
    })}
    {!!heldout.length && <section>
      <h3>Held-out · {heldout.length} frozen</h3>
      <p className="muted">Frozen before training · zero training rollouts</p>
      {heldout.map((env) => <EnvCard key={env.id} env={env} inspect={() => setInspectId(env.id)} />)}
    </section>}
  </div>;
}
