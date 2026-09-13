export type ConversationContext = { human_message?: string; bad_agent_output?: string };

export default function LessonContext({ context, reading = false }: { context?: ConversationContext; reading?: boolean }) {
  return <div className={`lesson-context ${reading ? 'reading' : ''}`} aria-label="Conversation being observed">
    {([['Codex output', context?.bad_agent_output], ['Your message', context?.human_message]] as const).map(([label, text]) => <section key={label}>
      <h3>{label}</h3><p>{text ? text.slice(0, 700) + (text.length > 700 ? '…' : '') : 'Reading this conversation…'}</p>
    </section>)}
  </div>;
}
