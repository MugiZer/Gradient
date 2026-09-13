import { motion, useReducedMotion } from 'motion/react';
import type { AgentRole, AgentState } from '../state/gradientMachine';
import { eyeMotion, spriteMotion } from '../motion/variants';

const bodies = {
  gradient: 'M8 5C12 2 23 3 26 8C29 12 27 16 28 20C29 26 23 29 17 28C11 30 5 26 4 21C2 15 4 9 8 5Z',
  observer: 'M11 4H21C23 4 24 6 25 9L29 18C30 21 25 28 22 28H10C7 28 2 21 3 18L7 9C8 6 9 4 11 4Z',
  builder: 'M8 4H24C27 4 29 7 29 10V24C29 27 26 29 23 29H9C5 29 3 26 3 23V10C3 6 5 4 8 4Z',
};
export default function AgentSprite({ role, state, size = 32 }: { role: AgentRole; state: AgentState; size?: number }) {
  const reduced = useReducedMotion();
  return <motion.svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true" className={`sprite sprite-${role}`}>
    <motion.g variants={spriteMotion} animate={reduced ? 'idle' : state} style={{ transformOrigin: '16px 20px' }}>
      <path d={bodies[role]} className="sprite-body" />
      <motion.g className="sprite-eyes" variants={eyeMotion} animate={reduced ? 'still' : state} style={{ transformOrigin: '16px 16px' }}>
        <rect x="10" y="12" width={role === 'observer' ? 4.5 : 4} height={state === 'done' ? 2 : 8} rx="2" />
        <rect x="19" y="12" width={role === 'observer' ? 4.5 : 4} height={state === 'done' ? 2 : 8} rx="2" />
      </motion.g>
      {state === 'done' && <path d="m22 25 2 2 4-5" fill="none" stroke="var(--accent)" strokeWidth="2" />}
      {state === 'attention' && <circle cx="27" cy="5" r="3" fill="var(--attention)" />}
    </motion.g>
  </motion.svg>;
}
