export default function ToolAction({ text, status }: { text: string; status?: string }) {
  return <details className="tool-action"><summary>{status === 'completed' ? '✓' : '›'} Tool action</summary><pre>{text}</pre></details>;
}
