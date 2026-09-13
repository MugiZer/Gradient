const http = require('node:http');
const { readFileSync, existsSync, createReadStream } = require('node:fs');
const { resolve, sep } = require('node:path');
const { evidenceDirectory, readTrainingEvidence } = require('./training-evidence.cjs');

function readDemo(repo) {
  const read = (path) => {
    const target = resolve(repo, path);
    if (!target.startsWith(resolve(repo) + sep)) throw new Error('Artifact outside repository');
    return JSON.parse(readFileSync(target, 'utf8'));
  };
  const fallback = read('runs/demo/fallback_proof.json');
  let current;
  try { current = read('runs/demo/current.json'); }
  catch { current = { pre: fallback.pre, training: { status: 'unavailable' }, post: { source: 'fallback', status: 'unavailable' } }; }
  let proof = null;
  if (current.post?.source === 'real' && current.post.artifact && existsSync(resolve(repo, current.post.artifact))) {
    const candidate = read(current.post.artifact);
    if (candidate.source === 'real' && candidate.schema_version === 1 && candidate.tasks?.length === 8 && ['pre', 'post'].every((phase) => {
      const rewards = candidate.tasks.map((task) => task[`${phase}_reward`]);
      return rewards.every((reward) => reward === 0 || reward === 1) && candidate[phase]?.score?.total === 8 && candidate[phase].score.passed === rewards.reduce((sum, reward) => sum + reward, 0);
    })) proof = candidate;
  }
  for (const artifact of [fallback, proof].filter(Boolean)) {
    for (const task of artifact.tasks) {
      for (const phase of ['pre', 'post']) {
        try { task[`${phase}_code`] ||= read(task[`${phase}_artifact`]).code; }
        catch { /* The artifact path remains visible when code is unavailable. */ }
      }
    }
  }
  const optional = (path) => { try { return read(path); } catch { return undefined; } };
  const root = current.experiment_id ? `runs/${current.experiment_id}` : null;
  const lesson = root ? {
    capability: optional(`${root}/capability.json`),
    tasks: [...(optional(`${root}/curriculum/train_specs.json`) || []), ...(optional(`${root}/curriculum/heldout_specs.json`) || [])],
    context: optional(`${root}/interaction.json`),
    primeRun: current.training?.run_id,
  } : undefined;
  let trainingEvidence, evidenceError;
  try { trainingEvidence = readTrainingEvidence(repo); }
  catch (error) { evidenceError = error.message; }
  return { current, fallback, proof, lesson, trainingEvidence, evidenceError };
}

async function serveDesktop(repo, backend) {
  const dist = resolve(repo, 'frontend/dist');
  const server = http.createServer((req, res) => {
    const pathname = new URL(req.url, 'http://localhost').pathname;
    if (pathname.startsWith('/evidence/')) {
      const name = pathname.slice('/evidence/'.length);
      const allowed = /^(gradient_training_evidence\.(png|pdf)|gradient_training_evidence_bundle\.zip|evidence\.json|sha256\.json|train_(fs_01|fs_02|json_03)_(prime_sample|pre|replay)\.json)$/;
      if (!allowed.test(name)) { res.writeHead(404).end(); return; }
      if (!['GET', 'HEAD'].includes(req.method)) { res.writeHead(405).end(); return; }
      const file = resolve(repo, evidenceDirectory, name);
      if (!existsSync(file)) { res.writeHead(404).end(); return; }
      const type = name.endsWith('.png') ? 'image/png' : name.endsWith('.pdf') ? 'application/pdf' : name.endsWith('.zip') ? 'application/zip' : 'application/json';
      res.setHeader('Content-Type', type);
      res.setHeader('X-Content-Type-Options', 'nosniff');
      res.setHeader('Content-Disposition', `${name.endsWith('.zip') ? 'attachment' : 'inline'}; filename="${name}"`);
      if (req.method === 'HEAD') { res.end(); return; }
      const stream = createReadStream(file);
      stream.on('error', () => res.destroy());
      stream.pipe(res);
      return;
    }
    if (pathname === '/desktop' || pathname.startsWith('/assets/')) {
      const file = pathname === '/desktop' ? resolve(dist, 'index.html') : resolve(dist, '.' + decodeURIComponent(pathname));
      if (!file.startsWith(dist + sep)) { res.writeHead(403).end(); return; }
      try {
        res.setHeader('Content-Type', file.endsWith('.js') ? 'text/javascript' : file.endsWith('.css') ? 'text/css' : 'text/html');
        res.end(readFileSync(file));
      } catch { res.writeHead(404).end(); }
      return;
    }
    const upstream = http.request(new URL(req.url, backend), { method: req.method, headers: req.headers }, (response) => {
      res.writeHead(response.statusCode, response.headers); response.pipe(res);
    });
    upstream.setTimeout(5000, () => upstream.destroy());
    upstream.on('error', () => { if (!res.headersSent) res.writeHead(503, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ detail: 'Connection lost. Saved results are available in Lesson history.' })); });
    req.pipe(upstream);
  });
  server.on('upgrade', (req, socket, head) => {
    const upstream = http.request(new URL(req.url, backend), { headers: req.headers });
    upstream.on('upgrade', (response, remote, remoteHead) => {
      socket.write('HTTP/1.1 101 Switching Protocols\r\n' + Object.entries(response.headers).map(([k, v]) => `${k}: ${v}`).join('\r\n') + '\r\n\r\n');
      if (remoteHead.length) socket.write(remoteHead);
      if (head.length) remote.write(head);
      socket.pipe(remote).pipe(socket);
      socket.on('error', () => remote.destroy()); remote.on('error', () => socket.destroy());
    });
    upstream.on('error', () => socket.destroy());
    upstream.on('response', () => socket.destroy());
    upstream.end();
  });
  await new Promise((done, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', done); });
  return { server, url: `http://127.0.0.1:${server.address().port}/desktop` };
}
module.exports = { readDemo, serveDesktop };
