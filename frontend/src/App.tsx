import { MotionConfig } from 'motion/react';
import DesktopCompanion from './gradient/DesktopCompanion';
import { springSoft } from './motion/springs';

export default function App() {
  if (!window.gradientDesktop) {
    return <main><p>Gradient's interface runs only in the Electron companion. The core tool is headless.</p></main>;
  }
  return <MotionConfig reducedMotion="user" transition={springSoft}><DesktopCompanion /></MotionConfig>;
}
