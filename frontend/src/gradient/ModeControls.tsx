export default function ModeControls({ mode, reset }: { mode: 'live' | 'experiment' | 'fallback'; reset?: () => void }) {
  return <nav className="mode-controls lesson-surface" aria-label="Lesson source">
    <select aria-label="Lesson source" value={mode} onChange={(event) => window.gradientDesktop?.mode(event.target.value as typeof mode)}>
      <option value="live">Live lesson</option><option value="fallback">Saved lesson</option><option value="experiment">Training</option>
    </select>
    {reset && <button className="text-button" onClick={reset} title="Return to the start of the saved lesson">Reset</button>}
  </nav>;
}
