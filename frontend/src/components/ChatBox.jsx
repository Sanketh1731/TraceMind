import React, { useState } from 'react';
import {
  MessageSquareIcon,
  XIcon,
  SparklesIcon,
  ArrowRightIcon
} from './Icons';

export default function ChatBox({ onClose, activeResult }) {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([
    {
      sender: "system",
      text: "TraceMind Copilot is grounded in your active diagnosis and indexed runbooks. Ask follow-up questions regarding remediation steps, command flags, or rollback procedures.",
    },
  ]);

  const suggestedPrompts = [
    "What is the rollback procedure?",
    "Can this fix cause cluster downtime?",
    "Show verified command flags",
    "Explain permission DACLs"
  ];

  const handleSend = (textToSend) => {
    const q = (textToSend || question).trim();
    if (!q) return;

    const userMsg = { sender: "user", text: q };
    setMessages((prev) => [...prev, userMsg]);
    setQuestion("");

    // Simulate grounded follow-up response
    setTimeout(() => {
      let replyText = "Based on the retrieved runbook: verify your file DACLs and restart the installer under elevated administrator privileges.";
      if (activeResult?.fix_steps?.length > 0) {
        replyText = `Regarding "${q}": prioritize executing Step 1 ("${activeResult.fix_steps[0].title}"). Verify exit status code 0 before proceeding to subsequent steps as specified in ${activeResult.citations?.[0]?.doc_id || "the runbook"}.`;
      }
      setMessages((prev) => [...prev, { sender: "bot", text: replyText }]);
    }, 500);
  };

  return (
    <div className="copilot-drawer" role="dialog" aria-label="Grounded Engineering Assistant">
      <div className="copilot-header">
        <div className="copilot-header-left">
          <MessageSquareIcon size={16} style={{ color: 'var(--accent-sky)' }} />
          <h4>TraceMind Copilot</h4>
          <span className="copilot-tag">Context-Aware</span>
        </div>
        <button className="copilot-close-btn" onClick={onClose} aria-label="Close assistant">
          <XIcon size={16} />
        </button>
      </div>

      <div className="copilot-messages-flow">
        {messages.map((m, i) => (
          <div key={i} className={`copilot-msg-card ${m.sender}`}>
            <span className="copilot-msg-meta">
              {m.sender === "user" ? "You" : m.sender === "system" ? "System" : "TraceMind"}
            </span>
            <div className="copilot-msg-bubble">{m.text}</div>
          </div>
        ))}
      </div>

      {/* Suggested Question Chips */}
      <div className="copilot-suggested-prompts">
        {suggestedPrompts.map((p, idx) => (
          <button
            key={idx}
            type="button"
            className="suggested-prompt-chip"
            onClick={() => handleSend(p)}
          >
            {p}
          </button>
        ))}
      </div>

      <form
        className="copilot-input-form"
        onSubmit={(e) => {
          e.preventDefault();
          handleSend();
        }}
      >
        <input
          type="text"
          className="copilot-input"
          placeholder="Ask a clarifying question about this fix..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button type="submit" className="copilot-send-btn" disabled={!question.trim()}>
          <ArrowRightIcon size={14} />
        </button>
      </form>
    </div>
  );
}
