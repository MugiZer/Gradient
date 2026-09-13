export function LessonSummary({ title }: { title: string }) {
  return <h2 className="lesson-title">{title === 'Observable Effect vs Simulation' ? <>Observable Effect<br />vs Simulation</> : title}</h2>;
}
export function TeachLessonButton({ teach, pending }: { teach: () => void; pending: boolean }) {
  return <button className="primary" disabled={pending} onClick={teach}>{pending ? 'Confirming…' : 'Teach lesson'}</button>;
}
export default function LessonPopover({ title, teach, dismiss, pending }: { title: string; teach: () => void; dismiss: () => void; pending: boolean }) {
  return <section aria-label="Possible lesson"><p className="eyebrow">✦ I noticed a correction</p><LessonSummary title={title} /><div className="actions"><TeachLessonButton teach={teach} pending={pending} /><button className="text-button" onClick={dismiss}>Dismiss</button></div></section>;
}
