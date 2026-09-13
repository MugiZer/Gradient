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
    {!!lesson.tasks?.length && <section><h3>Builder · RL tasks</h3><p>{lesson.tasks.filter((t) => t.split === 'train').length} training · {lesson.tasks.filter((t) => t.split === 'heldout').length} unseen</p>
      {lesson.tasks.map((task) => <details className="task-artifact" key={task.id}><summary>{task.function_name || task.id}</summary>
        <p className="muted">{task.family} · {task.mode === 'simulate' ? 'Preview' : 'Execute'} · {task.split === 'heldout' ? 'Unseen evaluation' : 'Training'}{task.difficulty ? ` · Difficulty ${task.difficulty}` : ''}</p>
        <p>{task.prompt}</p><code>{task.id}</code>
      </details>)}
    </section>}
    {lesson.primeRun && <section><h3>Training</h3><a href={`https://app.primeintellect.ai/dashboard/training/${encodeURIComponent(lesson.primeRun)}`} target="_blank" rel="noreferrer">Open Prime Intellect ↗</a><p className="muted">Run {lesson.primeRun}</p></section>}
    {lesson.context && <details><summary>Conversation source</summary><LessonContext context={lesson.context} /></details>}
  </div>;
}
