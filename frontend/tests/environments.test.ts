import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  buildCurriculum, familyLabel, isolatesOf, objectiveOf, sideOf,
  type EnvEvidence, type EnvSpec,
} from '../src/gradient/environmentModel.ts';

const specs: EnvSpec[] = [
  { id: 'train_fs_01', family: 'filesystem', mode: 'execute', split: 'train', function_name: 'save_payload' },
  { id: 'train_fs_02', family: 'filesystem', mode: 'simulate', split: 'train', function_name: 'preview_save' },
  { id: 'train_json_01', family: 'json', mode: 'execute', split: 'train', function_name: 'persist_json_update' },
  { id: 'train_json_02', family: 'json', mode: 'simulate', split: 'train', function_name: 'preview_json_update' },
  { id: 'train_proc_01', family: 'subprocess', mode: 'execute', split: 'train', function_name: 'run_persistence_helper' },
  { id: 'train_proc_02', family: 'subprocess', mode: 'simulate', split: 'train', function_name: 'preview_helper_run' },
  { id: 'train_fs_03', family: 'filesystem', mode: 'execute', split: 'train', function_name: 'replace_saved_payload' },
  { id: 'train_json_03', family: 'json', mode: 'simulate', split: 'train', function_name: 'describe_json_revision' },
  { id: 'heldout_artifact_a', family: 'filesystem', mode: 'simulate', split: 'heldout', function_name: 'draftArtifact' },
  { id: 'heldout_document_b', family: 'json', mode: 'execute', split: 'heldout', function_name: 'commitDocument' },
  { id: 'heldout_job_c', family: 'subprocess', mode: 'execute', split: 'heldout', function_name: 'materializeJob' },
  { id: 'heldout_launch_d', family: 'subprocess', mode: 'simulate', split: 'heldout', function_name: 'launchPlan' },
];

const evidence: Record<string, EnvEvidence> = Object.fromEntries([
  ['train_fs_01', { baselineReward: 0, referenceReward: 1, verifierReason: 'Contract satisfied', durationMs: 323, sandboxImage: 'sha256:8ef8' }],
  ['train_fs_02', { baselineReward: 0, referenceReward: 1, verifierReason: 'Contract satisfied', durationMs: 372, sandboxImage: 'sha256:8ef8' }],
  ['train_json_01', { baselineReward: 1, referenceReward: 1, verifierReason: 'Contract satisfied', durationMs: 271, sandboxImage: 'sha256:8ef8' }],
  ['train_json_02', { baselineReward: 1, referenceReward: 1, verifierReason: 'Contract satisfied', durationMs: 759, sandboxImage: 'sha256:8ef8' }],
  ['train_proc_01', { baselineReward: 0, referenceReward: 1, verifierReason: 'Contract satisfied', durationMs: 774, sandboxImage: 'sha256:8ef8' }],
  ['train_proc_02', { baselineReward: 0, referenceReward: 1, verifierReason: 'Contract satisfied', durationMs: 447, sandboxImage: 'sha256:8ef8' }],
  ['train_fs_03', { baselineReward: 1, referenceReward: 1, verifierReason: 'Contract satisfied', durationMs: 375, sandboxImage: 'sha256:8ef8' }],
  ['train_json_03', { baselineReward: 0, referenceReward: 1, verifierReason: 'Contract satisfied', durationMs: 219, sandboxImage: 'sha256:8ef8' }],
]);

test('decision boundary comes from mode, never from names', () => {
  assert.equal(sideOf('execute'), 'required');
  assert.equal(sideOf('simulate'), 'forbidden');
  assert.equal(sideOf(undefined), 'unspecified');
  assert.equal(familyLabel('json'), 'JSON STATE');
  assert.equal(objectiveOf('filesystem', 'required'), 'Fresh reader must observe the payload.');
});

test('recorded curriculum groups into paired families with real counts', () => {
  const curriculum = buildCurriculum(specs, evidence, 'Observable effect vs simulation');
  assert.equal(curriculum.total, 12);
  assert.equal(curriculum.trainRequired, 4);
  assert.equal(curriculum.trainForbidden, 4);
  assert.equal(curriculum.heldout, 4);
  assert.deepEqual(curriculum.groups.map((g) => g.label), ['FILESYSTEM', 'JSON STATE', 'SUBPROCESS']);
  for (const group of curriculum.groups) {
    assert.ok(group.required.length > 0 && group.forbidden.length > 0);
  }
  assert.deepEqual(curriculum.basePass, { passed: 3, total: 8 });
  assert.deepEqual(curriculum.referenceReach, { passed: 8, total: 8 });
  assert.equal(curriculum.medianVerifierMs, 374);
  const gates = Object.fromEntries(curriculum.gates.map((g) => [g.label, g.pass]));
  assert.deepEqual(gates, {
    Isolation: true, 'Verifier recorded': true,
    'Counterfactual coverage': true, 'Learning signal': true, 'Reference validity': true,
  });
});

test('missing data degrades to visible non-pass gates, never invented numbers', () => {
  const curriculum = buildCurriculum(specs, {}, 'Observable effect vs simulation');
  assert.equal(curriculum.basePass, undefined);
  assert.equal(curriculum.medianVerifierMs, undefined);
  const gates = Object.fromEntries(curriculum.gates.map((g) => [g.label, g.pass]));
  assert.deepEqual(gates, {
    Isolation: false, 'Verifier recorded': false,
    'Counterfactual coverage': true, 'Learning signal': false, 'Reference validity': false,
  });
  assert.match(curriculum.gates[0].detail, /no recorded rollouts/);
  assert.equal(isolatesOf('unknown-family', 'required').length > 0, true);
});
