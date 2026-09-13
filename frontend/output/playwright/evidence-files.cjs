const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { serveDesktop } = require('../../desktop/bridge.cjs');
const { evidenceDirectory, readTrainingEvidence } = require('../../desktop/training-evidence.cjs');

(async () => {
  const repo = resolve('..');
  const evidence = readTrainingEvidence(repo);
  assert.equal(evidence.examples.length, 3);
  for (const example of evidence.examples) {
    assert.equal(example.pre.reward, 0);
    assert.equal(example.replay.reward, 1);
    assert.equal(example.code, example.replay.code);
  }
  const { server, url } = await serveDesktop(repo, 'http://127.0.0.1:1');
  try {
    const origin = new URL(url).origin;
    for (const name of ['gradient_training_evidence.png', 'gradient_training_evidence.pdf', 'gradient_training_evidence_bundle.zip', 'evidence.json', 'train_fs_01_replay.json']) {
      const response = await fetch(`${origin}/evidence/${name}`);
      assert.equal(response.status, 200);
      const bytes = Buffer.from(await response.arrayBuffer());
      const original = readFileSync(resolve(repo, evidenceDirectory, name));
      assert.equal(createHash('sha256').update(bytes).digest('hex'), createHash('sha256').update(original).digest('hex'));
    }
    assert.equal((await fetch(`${origin}/evidence/%2e%2e%2f.env`)).status, 404);
    assert.equal((await fetch(`${origin}/evidence/evidence.json`, { method: 'POST' })).status, 405);
    console.log('PASS: evidence hashes, three comparisons, exact PNG/PDF/ZIP/JSON bytes without FastAPI, restricted file access');
  } finally { server.closeAllConnections(); server.close(); }
})().catch((error) => { console.error(error); process.exitCode = 1; });
