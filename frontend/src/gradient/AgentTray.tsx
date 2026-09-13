import { motion } from 'motion/react';
import AgentSprite from './AgentSprite';
import { spawn } from '../motion/variants';

export default function AgentTray({ builder, failed, peek }: { builder: boolean; failed: boolean; peek: (role: 'observer' | 'builder') => void }) {
  return <div className="agent-tray" aria-label="Learning agents">{(['observer', 'builder'] as const).map((role, index) => <motion.button key={role} custom={index} variants={spawn} initial="hidden" animate="visible" exit="hidden" aria-label={role === 'observer' ? 'Observer' : 'Environment Builder'} onMouseEnter={() => peek(role)} onFocus={() => peek(role)} onClick={() => peek(role)}>
    <AgentSprite role={role} state={failed ? 'attention' : role === 'observer' ? builder ? 'done' : 'thinking' : builder ? 'working' : 'idle'} />
  </motion.button>)}</div>;
}
