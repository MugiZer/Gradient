import { useState } from 'react';

export default function Composer({ disabled, send }: { disabled: boolean; send: (message: string) => Promise<boolean> }) {
  const [message, setMessage] = useState('');
  async function submit() {
    if (!disabled && message.trim() && await send(message.trim())) setMessage('');
  }
  return <form className="composer" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
    <textarea aria-label="Message Codex" placeholder="Ask Codex to work on something…" value={message} maxLength={16000} rows={2} onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => {
      if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void submit(); }
    }} />
    <div className="composer-footer"><span>Enter to send · Shift + Enter for a new line</span><button className="send-button" type="submit" disabled={disabled || !message.trim()} aria-label="Send message">↑</button></div>
  </form>;
}
