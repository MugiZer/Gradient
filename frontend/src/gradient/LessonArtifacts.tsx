import LessonContext, { type ConversationContext } from './LessonContext';

export type LessonEvidence = {
  capability?: { name?: string; description?: string; positive_rule?: string; negative_rule?: string };
  tasks?: { id: string; family?: string; mode?: string; prompt?: string; split: string; function_name?: string; difficulty?: number }[];
  context?: ConversationContext;
  primeRun?: string;
};

export default function LessonArtifacts({ lesson }: { lesson: LessonEvidence }) {
  return <div className="lesson-artifacts">
    {lesson.capability && <section><h3>Observer · Learning objective</h3><p>{lesson.capability.description || lesson.capability.name}</p>
      {lesson.capability.positive_rule && <p><strong>Do</strong> {lesson.capability.positive_rule}</p>}
      {lesson.capability.negative_rule && <p><strong>Avoid</strong> {lesson.capability.negative_rule}</p>}
    </section>}
    {lesson.primeRun && <section><h3>Training</h3><a href={`https://app.primeintellect.ai/dashboard/training/${encodeURIComponent(lesson.primeRun)}`} target="_blank" rel="noreferrer">Open Prime Intellect ↗</a><p className="muted">Run {lesson.primeRun}</p></section>}
    {lesson.context && <details><summary>Conversation source</summary><LessonContext context={lesson.context} /></details>}
  </div>;
}
