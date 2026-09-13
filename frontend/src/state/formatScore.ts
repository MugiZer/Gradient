export function formatScore(passed?: number, total?: number): string {
  return passed === undefined || !total ? 'Awaiting results' : `${Math.round(passed / total * 1000) / 10}%`;
}
