import { useState } from 'react';
import {
  isolatesOf, lessonTitleOf, objectiveOf, testOf, verifierIntentOf, REWARD_RULE,
  type Curriculum, type EnvView,
} from './environmentModel';
import { formatScore } from '../state/formatScore';

const shortHash = (hash?: string) => (hash ? hash.replace(/^sha256:/, '').slice(0, 12) : undefined);

const familyMeta = (env: EnvView) => {
  const family = env.family.toLowerCase() === 'json'
    ? 'JSON state'
    : `${env.familyLabel.charAt(0)}${env.familyLabel.slice(1).toLowerCase()}`;
  return `${family} · ${env.heldout ? 'Held-out' : 'Train'}`;
};

function Specification({ env, curriculum, back }: { env: EnvView; curriculum: Curriculum; back: () => void }) {
  const evidence = env.evidence;
  const frozen = evidence.verifiedAt ? new Date(evidence.verifiedAt) : undefined;
  return <div>
    <button className="text-button" onClick={back}>← Inspect</button>
    <p><strong>{lessonTitleOf(env.family, env.side)}</strong></p>
    <p className="muted">{objectiveOf(env.family, env.side)}</p>
    {env.prompt && <div className="env-step"><h4>Task</h4><p>{env.prompt}</p></div>}
    <div className="env-step"><h4>Implementation</h4>
      <p className="muted">{env.functionName} · {env.heldout ? 'held-out' : env.split}{typeof env.difficulty === 'number' ? ` · difficulty ${env.difficulty}` : ''}</p>
      <p className="muted">{env.sideLabel} · {env.familyLabel}</p>
      <p className="muted">Env {env.id}</p>
    </div>
    <div className="env-step"><h4>Verifier</h4>
      <p className="muted">{verifierIntentOf(env.family)}</p>
      <p className="muted">Reward rule: {REWARD_RULE}</p>
      {evidence.verifierReason && <p className="muted">{evidence.verifierReason}</p>}
      <p className="muted">
        {evidence.baselineReward === 0 || evidence.baselineReward === 1 ? `Baseline ${evidence.baselineReward}. ` : 'Baseline not recorded. '}
        {evidence.referenceReward === 0 || evidence.referenceReward === 1 ? `Reference ${evidence.referenceReward}.` : ''}
      </p>
      {typeof evidence.durationMs === 'number' && <p className="muted">Verifier {evidence.durationMs} ms</p>}
      {typeof evidence.seed === 'number' && <p className="muted">Seed {evidence.seed}</p>}
      {evidence.sandboxImage && <p className="muted">Sandbox {evidence.sandboxImage}</p>}
      {shortHash(evidence.envHash) && <p className="muted">Manifest {shortHash(evidence.envHash)}</p>}
      {evidence.verifiedAt && <p className="muted">Verified {evidence.verifiedAt}</p>}
    </div>
    {evidence.referenceCode && <details><summary>Reference code</summary><pre>{evidence.referenceCode}</pre></details>}
    {env.heldout
      ? <div className="env-step"><h4>Freeze</h4><p className="muted">
        {frozen && !isNaN(+frozen) ? `Verified ${frozen.toLocaleString()}. ` : ''}Zero training rollouts · verifier artifacts frozen.
        {shortHash(evidence.envHash) ? ` Manifest ${shortHash(evidence.envHash)}.` : ''}
      </p></div>
      : <div className="env-step"><h4>Calibration</h4><p className="muted">
        {curriculum.basePass ? `Base pass rate ${formatScore(curriculum.basePass.passed, curriculum.basePass.total)}. ` : 'No baseline rewards recorded. '}
        {curriculum.medianVerifierMs !== undefined ? `Median verifier ${curriculum.medianVerifierMs} ms. ` : ''}
        Rollout counts, flake rate, and failure mix not recorded.
      </p></div>}
    {!env.heldout && curriculum.referenceReach && <div className="env-step"><h4>Training value</h4><p className="muted">
      Before training: {curriculum.basePass ? formatScore(curriculum.basePass.passed, curriculum.basePass.total) : 'unknown'} ·{' '}
      Reference reach: {formatScore(curriculum.referenceReach.passed, curriculum.referenceReach.total)} (hand-authored reference, not trained weights).
    </p>
    {curriculum.primeRun && <a href={`https://app.primeintellect.ai/dashboard/training/${encodeURIComponent(curriculum.primeRun)}`} target="_blank" rel="noreferrer">Open Prime Intellect ↗</a>}
    </div>}
    <div className="env-step"><h4>Lesson quality</h4>
      <ul className="env-gates">{curriculum.gates.map((gate) => <li key={gate.label}>
        <strong className={gate.pass ? 'pass' : 'fail'}>{gate.pass ? '✓' : '×'} {gate.label}</strong> <span className="muted">— {gate.detail}</span>
      </li>)}</ul>
    </div>
    <details><summary>TaskSpec</summary><pre>{JSON.stringify({ id: env.id, family: env.family, side: env.side, split: env.split, function_name: env.functionName, difficulty: env.difficulty, prompt: env.prompt }, null, 2)}</pre></details>
  </div>;
}

export default function CurriculumExplorer({ curriculum }: { curriculum: Curriculum }) {
  const [exploring, setExploring] = useState(false);
  const [selectedId, setSelectedId] = useState<string>();
  const [specOpen, setSpecOpen] = useState(false);
  const all = curriculum.groups.flatMap((g) => [...g.required, ...g.forbidden, ...g.other]);
  const selected = (selectedId ? all.find((e) => e.id === selectedId) : undefined) || all[0];
  const train = curriculum.total - curriculum.heldout;

  if (!exploring) {
    return <div className="lesson-artifacts env-summary">
      <p className="eyebrow">Environment Builder</p>
      <p className="muted">Creating executable lessons</p>
      <p><strong>State &amp; side effects</strong></p>
      <p>{curriculum.capability || 'Observable effect vs simulation'}</p>
      <p className="muted">Teaching when an operation must change the world versus only describe it.</p>
      <p className="muted">{curriculum.total} RL environments · {train} train · {curriculum.heldout} held-out</p>
      {!!curriculum.total && <button className="primary" onClick={() => setExploring(true)}>Explore environments</button>}
    </div>;
  }

  const select = (env: EnvView) => { setSelectedId(env.id); setSpecOpen(false); };

  return <div className="lesson-artifacts env-explorer-expanded">
    <div className="env-explorer-head">
      <button className="text-button" onClick={() => { setExploring(false); setSpecOpen(false); }}>← Summary</button>
      <p><strong>State &amp; side effects</strong></p>
      <p className="muted">{curriculum.capability || 'Observable effect vs simulation'} · Teaching when an operation must change the world versus only describe it.</p>
      <p className="muted">{curriculum.total} RL environments · {train} train · {curriculum.heldout} held-out</p>
    </div>
    <div className="env-explorer-columns">
      <div className="env-collection">
        {curriculum.groups.map((group) => {
          const envs = [...group.required, ...group.forbidden, ...group.other];
          if (!envs.length) return null;
          return <section key={group.label || 'unlabeled'}>
            <h3>{group.label}</h3>
            {envs.map((env) => <button
              key={env.id}
              className={`env-item${selected?.id === env.id ? ' selected' : ''}`}
              aria-pressed={selected?.id === env.id}
              onClick={() => select(env)}
            >
              <span className="env-item-title">{lessonTitleOf(env.family, env.side)}</span>
              <span className="env-item-behavior muted">{objectiveOf(env.family, env.side)}</span>
              <span className="env-item-meta muted">{env.heldout ? 'Held-out' : 'Train'}</span>
            </button>)}
          </section>;
        })}
      </div>
      <div className="env-inspector" aria-live="polite">
        {!selected ? <p className="muted">Select an environment to inspect it.</p> : specOpen
          ? <Specification env={selected} curriculum={curriculum} back={() => setSpecOpen(false)} />
          : <div>
            <p><strong>{lessonTitleOf(selected.family, selected.side)}</strong></p>
            <p className="muted">{objectiveOf(selected.family, selected.side)}</p>
            <div className="env-step"><h4>Why this environment exists</h4><p className="muted">{isolatesOf(selected.family, selected.side)}</p></div>
            <div className="env-step"><h4>What is being tested</h4><p className="muted">{testOf(selected.family, selected.side)}</p></div>
            <p className="muted">{familyMeta(selected)}</p>
            <button className="text-button" onClick={() => setSpecOpen(true)}>View specification →</button>
          </div>}
      </div>
    </div>
  </div>;
}
