import React, { useState, useEffect, useRef } from 'react';
import {
  SearchIcon,
  TerminalIcon,
  BookOpenIcon,
  ZapIcon,
  TrashIcon,
  FileUpIcon,
  XIcon,
  CornerDownLeftIcon,
  SlidersIcon
} from './Icons';

export default function CommandPalette({
  isOpen,
  onClose,
  presets = [],
  documents = [],
  onSelectPreset,
  onDiagnose,
  onSelectDoc,
  onClearCache,
  forceRefresh,
  setForceRefresh,
  onTriggerUpload
}) {
  const [search, setSearch] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      setSearch("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  // Build searchable command list
  const actions = [
    {
      id: "action-diagnose",
      group: "Actions",
      label: "Execute TraceMind Diagnosis",
      desc: "Run hybrid retrieval and cross-encoder reranking pipeline",
      icon: <ZapIcon size={15} />,
      shortcut: "↵",
      onSelect: () => {
        onClose();
        onDiagnose();
      }
    },
    {
      id: "action-cache-toggle",
      group: "Settings",
      label: forceRefresh ? "Enable Semantic Cache" : "Bypass Semantic Cache",
      desc: forceRefresh ? "Currently bypassing cache for fresh inference" : "Currently reading from sub-10ms cache",
      icon: <SlidersIcon size={15} />,
      shortcut: "Toggle",
      onSelect: () => {
        setForceRefresh(!forceRefresh);
        onClose();
      }
    },
    {
      id: "action-upload",
      group: "Actions",
      label: "Ingest Runbook Document",
      desc: "Upload Markdown, Text, or PDF runbook into vector store",
      icon: <FileUpIcon size={15} />,
      shortcut: "Upload",
      onSelect: () => {
        onClose();
        onTriggerUpload();
      }
    },
    {
      id: "action-clear-cache",
      group: "Danger Zone",
      label: "Clear Semantic Vector Cache",
      desc: "Evict all cached diagnosis embeddings and query matches",
      icon: <TrashIcon size={15} />,
      shortcut: "Purge",
      onSelect: () => {
        onClose();
        onClearCache();
      }
    },
    ...presets.map((p, idx) => ({
      id: `preset-${idx}`,
      group: "Failure Presets",
      label: p.label,
      desc: p.desc,
      icon: <TerminalIcon size={15} />,
      shortcut: `Preset #${idx + 1}`,
      onSelect: () => {
        onSelectPreset(p.log);
        onClose();
      }
    })),
    ...documents.map((d) => ({
      id: `doc-${d.doc_id}`,
      group: "Indexed Runbooks",
      label: d.title,
      desc: `${d.chunk_count} embedded chunks in vector index`,
      icon: <BookOpenIcon size={15} />,
      shortcut: "View",
      onSelect: () => {
        onSelectDoc(d.doc_id);
        onClose();
      }
    }))
  ];

  // Filter commands by search query
  const filtered = actions.filter((item) => {
    const q = search.toLowerCase();
    return item.label.toLowerCase().includes(q) || item.desc.toLowerCase().includes(q) || item.group.toLowerCase().includes(q);
  });

  const handleKeyDown = (e) => {
    if (e.key === "Escape") {
      onClose();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % (filtered.length || 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filtered.length) % (filtered.length || 1));
    } else if (e.key === "Enter" && filtered.length > 0) {
      e.preventDefault();
      filtered[selectedIndex]?.onSelect();
    }
  };

  return (
    <div className="tm-modal-backdrop" onClick={onClose} onKeyDown={handleKeyDown}>
      <div className="tm-command-palette" onClick={(e) => e.stopPropagation()}>
        <div className="command-search-header">
          <SearchIcon size={18} className="command-search-icon" />
          <input
            ref={inputRef}
            type="text"
            className="command-search-input"
            placeholder="Type a command, search runbooks, or select failure preset..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setSelectedIndex(0);
            }}
          />
          <kbd className="command-esc-tag" onClick={onClose}>ESC</kbd>
        </div>

        <div className="command-results-list">
          {filtered.length === 0 ? (
            <div className="command-empty-state">No matching commands or runbooks found.</div>
          ) : (
            filtered.map((item, idx) => (
              <div
                key={item.id}
                className={`command-item ${idx === selectedIndex ? 'selected' : ''}`}
                onClick={item.onSelect}
                onMouseEnter={() => setSelectedIndex(idx)}
              >
                <div className="command-item-icon">{item.icon}</div>
                <div className="command-item-content">
                  <div className="command-item-title-row">
                    <span className="command-item-label">{item.label}</span>
                    <span className="command-item-group">{item.group}</span>
                  </div>
                  <span className="command-item-desc">{item.desc}</span>
                </div>
                {item.shortcut && (
                  <div className="command-item-shortcut">
                    <kbd>{item.shortcut}</kbd>
                    {idx === selectedIndex && <CornerDownLeftIcon size={12} className="enter-hint-icon" />}
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        <div className="command-palette-footer">
          <div className="footer-keys">
            <span><kbd>↑</kbd> <kbd>↓</kbd> to navigate</span>
            <span><kbd>↵</kbd> to select</span>
            <span><kbd>esc</kbd> to close</span>
          </div>
          <div className="footer-brand">TraceMind Command Hub</div>
        </div>
      </div>
    </div>
  );
}
