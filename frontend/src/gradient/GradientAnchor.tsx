import { motion } from 'motion/react';
import AgentSprite from './AgentSprite';
import type { AgentState } from '../state/gradientMachine';

export default function GradientAnchor({ state, onClick, expanded }: { state: AgentState; onClick: () => void; expanded: boolean }) {
  return <motion.button layout className="gradient-anchor" aria-label="Gradient" aria-expanded={expanded} onClick={onClick} title="Gradient"><AgentSprite role="gradient" state={state} /></motion.button>;
}
