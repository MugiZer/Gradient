import { MotionConfig } from 'motion/react';
import DesktopCompanion from './gradient/DesktopCompanion';
import { springSoft } from './motion/springs';

// The Electron companion is the only interface. It observes the real Codex
// task transcript and drives the real backend; there is no browser workspace.
export default function App() {
  return <MotionConfig reducedMotion="user" transition={springSoft}><DesktopCompanion /></MotionConfig>;
}
