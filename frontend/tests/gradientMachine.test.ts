import { test } from 'node:test';
import assert from 'node:assert/strict';
import { gradientReducer, initialGradient, type GradientModel, type BackendEvent } from '../src/state/gradientMachine.ts';

const apply = (state: GradientModel, type: string, data: Partial<BackendEvent> = {}) => gradientReducer(state, { type: 'event', event: { type, run_id: 'grad_test', ...data } });

test('only confirmation events deploy agents; dismiss and proof close preserve the workspace', () => {
  let state = apply(initialGradient, 'correction_candidate');
  assert.equal(state.stage, 'lesson_candidate');
  state = gradientReducer(state, { type: 'open' });
  assert.equal(state.stage, 'lesson_open');
  state = gradientReducer(state, { type: 'pending', operation: 'confirm' });
  assert.equal(state.stage, 'lesson_open');
  state = apply(state, 'lesson_confirmed');
  assert.equal(state.stage, 'observer_working');
  for (const [event, stage] of [['capability_extracted', 'builder_working'], ['curriculum_compiled', 'lesson_ready'], ['training_started', 'training'], ['training_completed', 'learned'], ['proof_started', 'proof']]) {
    state = apply(state, event);
    assert.equal(state.stage, stage);
  }
  assert.equal(gradientReducer(state, { type: 'close_proof' }).stage, 'learned');
  assert.equal(gradientReducer(apply(initialGradient, 'correction_candidate'), { type: 'dismiss' }).stage, 'idle');
});

test('real scores are deduplicated, scoped to a run, and never manufactured', () => {
  let state = apply(initialGradient, 'correction_candidate');
  assert.deepEqual(state.baseline, []);
  const event = { task_id: 'task_8', split: 'heldout', reward: 1 };
  state = apply(apply(state, 'baseline_result', event), 'baseline_result', event);
  assert.equal(state.baseline.length, 1);
  state = apply(state, 'heldout_result', { ...event, run_id: 'grad_other' });
  assert.deepEqual(state.trained, []);
  state = apply(state, 'baseline_result', { ...event, split: 'train', task_id: 'train_1' });
  assert.equal(state.baseline.length, 1);
  state = apply(state, 'proof_started', { task_id: 'task_8' });
  state = apply(state, 'comparison_result', { task_id: 'wrong', label: 'base', reward: 1 });
  assert.deepEqual(state.comparison, {});
  state = apply(state, 'comparison_result', { task_id: 'task_8', label: 'base', reward: 0, code: 'return preview' });
  assert.equal(state.comparison.base?.reward, 0);
});

test('failed requests remain retryable without a tenth stage or artificial progress', () => {
  let state = apply(initialGradient, 'curriculum_compiled', { train_count: 8, unseen_count: 4 });
  state = apply(state, 'state', { state: 'TRAINING' });
  assert.equal(state.stage, 'lesson_ready');
  state = apply(state, 'state', { state: 'FAILED', error: 'Missing training config' });
  assert.equal(state.stage, 'lesson_ready');
  assert.equal(state.error, 'Missing training config');
  state = gradientReducer(state, { type: 'pending' });
  assert.equal(state.error, 'Missing training config');
  assert.equal(state.progress, undefined);
});
