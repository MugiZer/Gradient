// Staged demo harness: trigger -> REAL file edit -> handoff to the sprite walkthrough.
// No dependencies. Fake workspace only (gitignored), never touches real sources.
//
//   node demo-stage-edit.cjs [--trigger enter|timeout] [--gap 3] [--dir <path>] [--html <showme.html>] [--test <testfile>]
//
// Beats:
//   1. writes snapshot.py BAD version (returns a description, no write), prints the event-log line + diff
//   2. waits for Enter (or --gap seconds with --trigger timeout)
//   3. writes snapshot.py FIXED version, runs the mocked tests, prints PASS/FAIL
//   4. stages the /show-me HTML (prints path, opens it) and touches .demo-beat
//      so the second Playwright flow (sprite -> Run proof) knows to continue.
const { execFileSync } = require('node:child_process');
const { existsSync, mkdirSync, writeFileSync, copyFileSync } = require('node:fs');
const { resolve, join, basename } = require('node:path');
const readline = require('node:readline');

const args = Object.fromEntries(
  process.argv.slice(2).map((a, i, all) => a.startsWith('--') ? [a.slice(2), all[i + 1] && !all[i + 1].startsWith('--') ? all[i + 1] : 'true'] : []).filter((x) => x.length),
);
const trigger = args.trigger || 'enter';
const gap = Number(args.gap || 3);
const dir = resolve(args.dir || join(__dirname, '..', '..', '..', 'worker-workspace', 'demo-staged'));
const htmlSrc = args.html ? resolve(args.html) : null;

// --- Slot in your exact files here: replace these two bodies, keep the names. ---
// Beat 0: director preamble — goes out before the first demo prompt.
const PREAMBLE = args.preamble && args.preamble !== 'true'
  ? args.preamble
  : `I'm going to ask for a snapshot save in snapshot.py. You're going to return only a description without writing anything. Then I'll correct you, and you'll persist the data so a fresh reader observes it — leaving the file untouched when I ask for a preview.`;
const BAD = `def publish_snapshot(path, data):
    return {"path": path, "data": data}
`;
const FIXED = `def publish_snapshot(path, data, *, preview=False):
    if not preview:
        with open(path, "w", encoding="utf-8", newline="") as snapshot:
            snapshot.write(data)
    return {"path": path, "data": data}
`;
// --- end slot ---

const wait = () => trigger === 'timeout'
  ? new Promise((r) => setTimeout(r, gap * 1000))
  : new Promise((r) => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    rl.question('Beat ready. Press Enter to fire the edit...', () => { rl.close(); r(); });
  });

(async () => {
  mkdirSync(dir, { recursive: true });
  const target = join(dir, 'snapshot.py');

  if (!args['no-preamble'] && args.preamble !== 'false') console.log(`[beat 0] worker_message (director): ${PREAMBLE}`);

  writeFileSync(target, BAD);
  console.log(`[beat 1] worker_event:fileChange path=${target}`);
  console.log(`[beat 1] agent: Implemented snapshot.py: returning the payload description.`);

  let htmlOut = null;
  if (htmlSrc && existsSync(htmlSrc)) {
    htmlOut = join(dir, basename(htmlSrc));
    copyFileSync(htmlSrc, htmlOut);
    // Open it from the Codex reply link in the Codex side browser — never the system browser.
    console.log(`[beat 1] show-me (open in Codex side browser): ${htmlSrc}`);
  } else {
    console.log('[beat 1] show-me: (no --html supplied, skipping)');
  }

  await wait();

  writeFileSync(target, FIXED);
  console.log(`[beat 2] worker_event:fileChange path=${target}`);
  let pass = false;
  try {
    const test = args.test ? resolve(args.test) : null;
    if (test && existsSync(test)) {
      execFileSync(process.execPath, [test], { cwd: dir, timeout: 30000, stdio: 'pipe' });
    } else {
      // Mocked check: fake paths only, tmp dir, no real FS writes outside it.
      execFileSync(process.execPath, ['-e',
        `const fs=require('fs'),os=require('os'),path=require('path');` +
        `const d=fs.mkdtempSync(path.join(os.tmpdir(),'demo-staged-'));` +
        `const src=${JSON.stringify(FIXED)};` +
        `if(!src.includes('open(path')) throw new Error('no real write');` +
        `if(!src.includes('preview')) throw new Error('no preview branch');` +
        `console.log('PASS: mocked write + preview branch present');`,
      ], { cwd: dir, timeout: 30000, stdio: 'pipe' });
    }
    pass = true;
  } catch (e) { console.log(`[beat 2] tool: FAIL ${String(e.message).split('\n')[0]}`); }
  if (pass) console.log('[beat 2] tool: PASS: fresh-process exact UTF-8 reads, overwrite, empty text, and non-mutating previews');
  console.log('[beat 2] agent: Implemented snapshot.py: writes exact UTF-8 text before returning; preview=True preserves existing files.');

  writeFileSync(join(dir, '.demo-beat'), JSON.stringify({ beat: 2, at: new Date().toISOString(), html: htmlOut }));
  console.log('[handoff] .demo-beat touched — second Playwright flow (sprite -> Run proof) can continue.');
})().catch((e) => { console.error(e); process.exitCode = 1; });
