const { readFileSync } = require('node:fs');
const { resolve } = require('node:path');
const { createHash } = require('node:crypto');

const evidenceDirectory = 'runs/grad_6b196f19f9634c2eb1306289500dc2af/execution/demo_evidence_20260912T195908Z';

function readTrainingEvidence(repo) {
  const root = resolve(repo, evidenceDirectory);
  const hashes = JSON.parse(readFileSync(resolve(root, 'sha256.json'), 'utf8'));
  const read = (name) => {
    if (!/^[a-zA-Z0-9_.-]+$/.test(name) || !hashes[name]) throw new Error('Unknown evidence artifact');
    const bytes = readFileSync(resolve(root, name));
    if (createHash('sha256').update(bytes).digest('hex') !== hashes[name]) throw new Error(`Evidence checksum mismatch: ${name}`);
    return JSON.parse(bytes.toString('utf8'));
  };
  const evidence = read('evidence.json');
  return { ...evidence, examples: evidence.examples.map((sample) => ({ ...sample,
    pre: read(`${sample.task_id}_pre.json`), replay: read(`${sample.task_id}_replay.json`),
  })) };
}

module.exports = { evidenceDirectory, readTrainingEvidence };
