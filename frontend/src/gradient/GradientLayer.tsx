import { useEffect, useRef, type Dispatch, type ReactNode } from 'react';
import { AnimatePresence, LayoutGroup, motion } from 'motion/react';
import type { Action, GradientModel } from '../state/gradientMachine';
import { springSoft } from '../motion/springs';
import { surface } from '../motion/variants';
import GradientAnchor from './GradientAnchor';
import LessonNudge from './LessonNudge';
import LessonPopover from './LessonPopover';
import AgentTray from './AgentTray';
import AgentPeek from './AgentPeek';
import LessonArtifact from './LessonArtifact';
import TrainingProgress from './TrainingProgress';
import LearnedArtifact from './LearnedArtifact';
import ProofDrawer, { type ProofContext } from './ProofDrawer';
import TechnicalDetails from './TechnicalDetails';

export type LessonCommand = 'confirm' | 'dismiss' | 'train' | 'proof';
export default function GradientLayer({ model: m, dispatch, command, inspect, connectionDetails, proofContext, activity }: { model: GradientModel; dispatch: Dispatch<Action>; command: (action: LessonCommand) => void; inspect: (runId: string) => Promise<void>; connectionDetails?: ReactNode; proofContext?: ProofContext; activity?: ReactNode }) {
  const root = useRef<HTMLDivElement>(null);
  const agents = !activity && (m.stage === 'observer_working' || m.stage === 'builder_working');
  const panelStage = m.stage === 'lesson_open' || ['lesson_ready', 'training', 'learned'].includes(m.stage);
  const panel = !activity && !m.peek && panelStage && m.disclosure !== 'closed';
  const details = () => { dispatch({ type: 'peek', peek: 'details' }); if (m.runId) void inspect(m.runId); };
  const closePeek = () => { dispatch({ type: 'peek' }); root.current?.querySelector<HTMLButtonElement>('.gradient-anchor')?.focus(); };
  useEffect(() => {
    if (m.stage === 'lesson_open') root.current?.querySelector<HTMLButtonElement>('.primary')?.focus();
  }, [m.stage]);
  return <LayoutGroup id="gradient"><div ref={root} className="gradient-layer" data-stage={m.stage} onKeyDown={(event) => {
    if (event.key === 'Escape') {
      if (m.peek) closePeek();
      else if (m.stage === 'lesson_open') { command('dismiss'); root.current?.querySelector<HTMLButtonElement>('.gradient-anchor')?.focus(); }
    }
  }}>
    <div className="gradient-status" role="status" aria-live="polite">{m.stage.replaceAll('_', ' ')}</div>
    <AnimatePresence>
      {m.peek && !activity && <motion.div key="peek" className="peek-surface" variants={surface} initial="hidden" animate="visible" exit="hidden">
        {m.peek === 'details' ? <TechnicalDetails events={m.events} artifacts={m.artifacts} runId={m.runId} close={closePeek}>{connectionDetails}</TechnicalDetails> : <AgentPeek role={m.peek} title={m.title} complete={m.tasks.length} total={m.totalTasks} done={m.stage === 'builder_working'} details={details} close={closePeek} />}
      </motion.div>}
    </AnimatePresence>
    <motion.div layout transition={springSoft} className={`gradient-object ${panel || activity ? 'expanded' : ''}`}>
      <AnimatePresence mode="popLayout">
        {activity && <motion.div key="activity" className="lesson-surface" variants={surface} initial="hidden" animate="visible" exit="hidden">{activity}</motion.div>}
        {panel && <motion.div key={m.stage} layoutId="gradient-surface" className="lesson-surface" variants={surface} initial="hidden" animate="visible" exit="hidden">
          {m.stage === 'lesson_open' && <LessonPopover title={m.title} pending={!!m.pending} teach={() => command('confirm')} dismiss={() => command('dismiss')} />}
          {m.stage === 'lesson_ready' && <LessonArtifact title={m.title} train={m.trainCount} unseen={m.unseenCount} pending={!!m.pending} start={() => command('train')} details={details} />}
          {m.stage === 'training' && <TrainingProgress progress={m.progress} run={m.primeRun} details={details} reference={proofContext?.reference} />}
          {m.stage === 'learned' && <LearnedArtifact title={m.title} base={m.baseline} trained={m.trained} pending={!!m.pending} proof={() => command('proof')} details={details} reference={proofContext?.reference} />}
        </motion.div>}
        {agents && <motion.div layoutId="gradient-surface" key="agents" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><AgentTray builder={m.stage === 'builder_working'} failed={!!m.error} peek={(peek) => dispatch({ type: 'peek', peek })} /></motion.div>}
        {m.stage === 'lesson_candidate' && !activity && <motion.div key="nudge" variants={surface} initial="hidden" animate="visible" exit="hidden"><LessonNudge open={() => dispatch({ type: 'open' })} /></motion.div>}
        {!panel && !agents && !activity && m.stage !== 'lesson_candidate' && <motion.span key="origin" layoutId="gradient-surface" className="anchor-origin" aria-hidden="true" />}
      </AnimatePresence>
      <GradientAnchor state={m.error ? 'attention' : m.stage === 'lesson_candidate' ? 'noticing' : agents ? 'working' : 'idle'} expanded={panel || !!m.peek} onClick={() => m.stage === 'lesson_candidate' ? dispatch({ type: 'open' }) : panelStage ? dispatch({ type: 'toggle_disclosure' }) : m.peek ? closePeek() : details()} />
    </motion.div>
    {m.error && m.stage !== 'proof' && <div className="gradient-error" role="alert"><p>Gradient needs attention.</p><details><summary>View details</summary><p>{m.error}</p></details><button className="text-button" onClick={() => dispatch({ type: 'clear_error' })}>Dismiss</button></div>}
    <AnimatePresence>{m.stage === 'proof' && <ProofDrawer key="proof" results={m.comparison} error={m.error} context={proofContext} close={() => { dispatch({ type: 'close_proof' }); root.current?.querySelector<HTMLButtonElement>('.gradient-anchor')?.focus(); }} />}</AnimatePresence>
  </div></LayoutGroup>;
}
