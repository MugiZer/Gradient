import type { Variants } from 'motion/react';
import { springSpawn, timing } from './springs';

export const surface: Variants = {
  hidden: { opacity: 0, scale: 0.82, y: 20, transition: { duration: timing.fast } },
  visible: { opacity: 1, scale: 1, y: 0, transition: { duration: timing.normal } },
};
export const spawn: Variants = {
  hidden: (index: number) => ({ opacity: 0, scale: 0.4, x: index === 0 ? 'var(--spawn-observer)' : 'var(--spawn-builder)', y: 0 }),
  visible: (index: number) => ({ opacity: 1, scale: 1, x: 0, y: 0, transition: { ...springSpawn, delay: index * timing.stagger } }),
};
export const spriteMotion: Variants = {
  idle: { y: 0, scale: 1 },
  noticing: { y: [0, -6, 0, -3, 0], scale: [1, 1.06, 0.97, 1.02, 1], transition: { type: 'tween', duration: timing.large * 2, times: [0, 0.3, 0.55, 0.8, 1], repeat: 1, repeatDelay: timing.fast } },
  thinking: { scale: [1, 1.04, 1], transition: { type: 'tween', duration: timing.pulse, repeat: Infinity } },
  working: { y: [0, -1.5, 0], transition: { type: 'tween', duration: timing.pulse, repeat: Infinity } },
  done: { y: 0, scale: 1 },
  attention: { y: -2, scale: 1 },
};
export const eyeMotion: Variants = {
  still: { scaleY: 1, x: 0, y: 0 },
  idle: { scaleY: [1, 1, 0.15, 1, 1], x: 0, y: 0, transition: { type: 'tween', duration: timing.blink, times: [0, 0.9, 0.92, 0.94, 1], repeat: Infinity } },
  noticing: { x: 0, y: -2, scaleY: [1, 1.25, 1], transition: { type: 'tween', duration: timing.large * 2, times: [0, 0.5, 1], repeat: 1, repeatDelay: timing.fast } },
  thinking: { x: [0, 1, 0], scaleY: 1, transition: { type: 'tween', duration: timing.pulse, repeat: Infinity } },
  working: { x: 0, y: 0, scaleY: 1 },
  done: { x: 0, y: 3, scaleY: 1 },
  attention: { x: 0, y: -1, scaleY: 1 },
};
