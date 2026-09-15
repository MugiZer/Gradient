import { motion } from 'motion/react';
import type { MouseEvent } from 'react';
import AgentSprite from './AgentSprite';
import type { AgentState } from '../state/gradientMachine';

export default function GradientAnchor({ state, onClick, expanded, onAnchor }: { state: AgentState; onClick: () => void; expanded: boolean; onAnchor?: (event: MouseEvent) => boolean | void }) {
  return <motion.button layout className="gradient-anchor" aria-label="Gradient" aria-expanded={expanded} onClick={(event) => { if (onAnchor?.(event) === true) return; onClick(); }} title="Gradient"><AgentSprite role="gradient" state={state} /></motion.button>;
}
