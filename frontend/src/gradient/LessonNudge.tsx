export default function LessonNudge({ open }: { open: () => void }) {
  return <button className="lesson-nudge" onClick={open}>✦ Lesson found</button>;
}
