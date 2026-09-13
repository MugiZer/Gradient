export default function DiffPreview({ text }: { text: string }) {
  return <details className="diff-preview"><summary>Changes</summary><pre>{text}</pre></details>;
}
