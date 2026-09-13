import { MotionConfig } from 'motion/react';
import CodexWorkspace from './codex/CodexWorkspace';
import { springSoft } from './motion/springs';
import DesktopCompanion from './gradient/DesktopCompanion';

export default function App() {
  if (location.pathname === '/desktop') return <MotionConfig reducedMotion="user" transition={springSoft}><DesktopCompanion /></MotionConfig>;
  if (location.pathname !== '/' && !(import.meta.env.DEV && location.pathname === '/dev/ui')) return <main><p>Page not found.</p><a href="/">Return to Codex</a></main>;
  return <MotionConfig reducedMotion="user" transition={springSoft}><CodexWorkspace showcase={import.meta.env.DEV && location.pathname === '/dev/ui'} /></MotionConfig>;
}
