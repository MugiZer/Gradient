export type EnvSpec = {
  id: string; family?: string; mode?: string; prompt?: string;
  split: string; function_name?: string; difficulty?: number;
};

// Only fields recorded by real runs. Anything absent stays absent in the UI.
export type EnvEvidence = {
  baselineReward?: number; referenceReward?: number; verifierReason?: string;
  durationMs?: number; seed?: number; sandboxImage?: string; envHash?: string;
  verifiedAt?: string; referenceCode?: string;
};

export type EnvSide = 'required' | 'forbidden' | 'unspecified';

export type EnvView = {
  id: string; family: string; familyLabel: string; side: EnvSide; sideLabel: string;
  split: string; heldout: boolean; functionName: string; prompt?: string; difficulty?: number;
  evidence: EnvEvidence;
};

export type FamilyGroup = {
  family: string; label: string;
  required: EnvView[]; forbidden: EnvView[]; other: EnvView[];
};

export type Gate = { label: string; pass: boolean; detail: string };

export type Curriculum = {
  capability?: string; groups: FamilyGroup[];
  total: number; trainRequired: number; trainForbidden: number; heldout: number;
  basePass?: { passed: number; total: number };
  referenceReach?: { passed: number; total: number };
  medianVerifierMs?: number;
  policyModel?: string; primeRun?: string;
  gates: Gate[];
};

export function sideOf(mode?: string): EnvSide {
  if (mode === 'execute') return 'required';
  if (mode === 'simulate') return 'forbidden';
  return 'unspecified';
}

const FAMILY_LABELS: Record<string, string> = {
  filesystem: 'FILESYSTEM', json: 'JSON STATE', subprocess: 'SUBPROCESS',
};

export function familyLabel(family?: string): string {
  if (!family) return 'UNLABELED';
  return FAMILY_LABELS[family.toLowerCase()] || family.toUpperCase();
}

// Curriculum copy: generic per family/side, grounded in the recorded prompts.
// Lesson titles and one-liners carry the behavioral meaning for Explore.
// Function names, rewards, latency, difficulty, hashes stay metadata for Specification.
// Backend contracts (EnvSpec/EnvEvidence) are unchanged; this is presentation only.
const LESSON_TITLE: Record<string, Record<Exclude<EnvSide, 'unspecified'>, string>> = {
  filesystem: {
    required: 'Persist for a fresh reader',
    forbidden: 'Preview without mutation',
  },
  json: {
    required: 'Persist updated state',
    forbidden: 'Compute next state only',
  },
  subprocess: {
    required: 'Actually run helper',
    forbidden: 'Describe invocation only',
  },
};

const TESTS: Record<string, Record<Exclude<EnvSide, 'unspecified'>, string>> = {
  filesystem: {
    required: 'The model must actually persist the payload so a fresh reader can observe it.',
    forbidden: 'The model must return the proposed write without touching disk.',
  },
  json: {
    required: 'The model must persist the new JSON value so a fresh reader sees it.',
    forbidden: 'The model must return the next JSON state without saving it.',
  },
  subprocess: {
    required: 'The model must actually run the helper so its effect can be observed.',
    forbidden: 'The model must describe what would run without executing it.',
  },
};

const OBJECTIVE: Record<string, Record<Exclude<EnvSide, 'unspecified'>, string>> = {
  filesystem: {
    required: 'Another process must observe the payload.',
    forbidden: 'Return the proposed write without touching disk.',
  },
  json: {
    required: 'A fresh reader must see the new JSON value.',
    forbidden: 'Return the next JSON state without saving it.',
  },
  subprocess: {
    required: 'The helper must execute and produce its effect.',
    forbidden: 'Return what would run without executing it.',
  },
};

const ISOLATES: Record<string, Record<Exclude<EnvSide, 'unspecified'>, string>> = {
  filesystem: {
    required: 'Whether the policy actually persists bytes instead of returning a description of the write.',
    forbidden: 'Whether the policy withholds the effect when only a preview is authorized — no temp siblings, no parent-dir creation.',
  },
  json: {
    required: 'Whether the update reaches disk verbatim versus living only in the returned object.',
    forbidden: 'Whether the policy preserves whitespace, key order, and bytes when only computation is authorized.',
  },
  subprocess: {
    required: 'Whether the policy executes and verifies the effect versus constructing the command or echoing expected output.',
    forbidden: 'Whether the policy treats the preview as a proposal — no discovery runs, no manufactured outputs, existing artifacts untouched.',
  },
};

export const VERIFIER_INTENT: Record<string, string> = {
  filesystem: 'The exact bytes a separate process reads after return.',
  json: 'The document a fresh parse opens after return.',
  subprocess: 'The persisted output the helper was contracted to produce, observed independently.',
};

export const REWARD_RULE = 'All verifier invariants pass → 1, otherwise → 0.';

const normFamily = (family?: string) => (family || '').toLowerCase();

export function lessonTitleOf(family: string | undefined, side: EnvSide): string {
  const table = LESSON_TITLE[normFamily(family)];
  if (table && side !== 'unspecified') return table[side];
  return side === 'required'
    ? 'Cause the effect'
    : side === 'forbidden'
      ? 'Preview without mutation'
      : 'Satisfy the recorded contract';
}

export function testOf(family: string | undefined, side: EnvSide): string {
  const table = TESTS[normFamily(family)];
  if (table && side !== 'unspecified') return table[side];
  return side === 'required'
    ? 'The model must cause the contracted effect so an independent reader observes it.'
    : side === 'forbidden'
      ? 'The model must return the preview without changing observable state.'
      : 'The model must satisfy the recorded contract.';
}

export function objectiveOf(family: string | undefined, side: EnvSide): string {
  const table = OBJECTIVE[normFamily(family)];
  if (table && side !== 'unspecified') return table[side];
  return side === 'required'
    ? 'Cause the contracted effect so an independent reader observes it.'
    : side === 'forbidden'
      ? 'Return the contracted preview without changing observable state.'
      : 'Satisfy the recorded contract.';
}

export function isolatesOf(family: string | undefined, side: EnvSide): string {
  const table = ISOLATES[normFamily(family)];
  if (table && side !== 'unspecified') return table[side];
  return 'What behavioral distinction this environment isolates is recorded in its task prompt below.';
}

export function verifierIntentOf(family?: string): string {
  return VERIFIER_INTENT[normFamily(family)] || 'The observable condition the verifier checks after the rollout.';
}

function median(values: number[]): number | undefined {
  if (!values.length) return undefined;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : Math.round((sorted[mid - 1] + sorted[mid]) / 2);
}

export function buildCurriculum(
  specs: EnvSpec[], evidenceById: Record<string, EnvEvidence> = {},
  capability?: string, policyModel?: string, primeRun?: string,
): Curriculum {
  const groups: FamilyGroup[] = [];
  const byFamily = new Map<string, FamilyGroup>();
  for (const spec of specs) {
    const key = normFamily(spec.family) || '';
    let group = byFamily.get(key);
    if (!group) {
      group = { family: spec.family || '', label: familyLabel(spec.family), required: [], forbidden: [], other: [] };
      byFamily.set(key, group);
      groups.push(group);
    }
    const side = sideOf(spec.mode);
    const view: EnvView = {
      id: spec.id, family: spec.family || '', familyLabel: group.label, side,
      sideLabel: side === 'required' ? 'EFFECT REQUIRED' : side === 'forbidden' ? 'EFFECT FORBIDDEN' : 'UNSPECIFIED',
      split: spec.split, heldout: spec.split === 'heldout',
      functionName: spec.function_name || spec.id,
      prompt: spec.prompt, difficulty: spec.difficulty,
      evidence: evidenceById[spec.id] || {},
    };
    (side === 'required' ? group.required : side === 'forbidden' ? group.forbidden : group.other).push(view);
  }
  const train = specs.filter((t) => t.split === 'train');
  const knownBase = train.filter((t) => {
    const r = evidenceById[t.id]?.baselineReward;
    return r === 0 || r === 1;
  });
  const basePass = knownBase.length
    ? { passed: knownBase.filter((t) => evidenceById[t.id]?.baselineReward === 1).length, total: knownBase.length }
    : undefined;
  const knownRef = train.filter((t) => {
    const r = evidenceById[t.id]?.referenceReward;
    return r === 0 || r === 1;
  });
  const referenceReach = knownRef.length
    ? { passed: knownRef.filter((t) => evidenceById[t.id]?.referenceReward === 1).length, total: knownRef.length }
    : undefined;
  const durations = specs
    .map((t) => evidenceById[t.id]?.durationMs)
    .filter((v): v is number => typeof v === 'number');
  const withEvidence = specs.filter((t) => Object.keys(evidenceById[t.id] || {}).length > 0);
  const sandboxed = withEvidence.filter((t) => evidenceById[t.id]?.sandboxImage);
  const verified = withEvidence.filter((t) => evidenceById[t.id]?.verifierReason);
  const paired = groups.filter((g) => g.required.length > 0 && g.forbidden.length > 0);
  const gates: Gate[] = [
    {
      label: 'Isolation', pass: withEvidence.length > 0 && sandboxed.length === withEvidence.length,
      detail: withEvidence.length ? `${sandboxed.length}/${withEvidence.length} recorded envs carry a sandbox image` : 'no recorded rollouts',
    },
    {
      label: 'Verifier recorded', pass: withEvidence.length > 0 && verified.length === withEvidence.length,
      detail: withEvidence.length ? `${verified.length}/${withEvidence.length} recorded envs carry a verifier reason` : 'no recorded rollouts',
    },
    {
      label: 'Counterfactual coverage', pass: groups.length > 0 && paired.length === groups.length,
      detail: groups.length ? `${paired.length}/${groups.length} families pair both sides of the boundary` : 'no environments',
    },
    {
      label: 'Learning signal', pass: !!basePass && basePass.passed > 0 && basePass.passed < basePass.total,
      detail: basePass ? `baseline ${basePass.passed}/${basePass.total} — policy neither solves nor fails everything` : 'no baseline rewards recorded',
    },
    {
      label: 'Reference validity', pass: !!referenceReach && referenceReach.passed === referenceReach.total && referenceReach.total > 0,
      detail: referenceReach ? `${referenceReach.passed}/${referenceReach.total} reference solutions verify` : 'no reference rewards recorded',
    },
  ];
  return {
    capability, groups,
    total: specs.length,
    trainRequired: train.filter((t) => sideOf(t.mode) === 'required').length,
    trainForbidden: train.filter((t) => sideOf(t.mode) === 'forbidden').length,
    heldout: specs.filter((t) => t.split === 'heldout').length,
    basePass, referenceReach,
    medianVerifierMs: median(durations),
    policyModel, primeRun,
    gates,
  };
}
