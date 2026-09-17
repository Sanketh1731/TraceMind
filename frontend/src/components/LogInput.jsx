import React, { useState, useEffect, useRef } from 'react';
import {
  TerminalIcon,
  ZapIcon,
  ChevronDownIcon,
  FileUpIcon,
  SlidersIcon,
  AlertTriangleIcon
} from './Icons';

export const PRESETS = [
  {
    label: "Windows 0x80070005",
    desc: "Installer Access Denied (DACL permissions failure)",
    log: "Error: 0x80070005 Access Denied while installing package at C:\\Users\\HP\\AppData\\Local\\Temp\\setup.msi",
    category: "Windows"
  },
  {
    label: "Docker OOMKilled 137",
    desc: "Container worker killed by Linux cgroup enforcer",
    log: "Error: container worker-task-9a2 was killed (exit code 137): OOMKilled by Linux cgroup enforcer",
    category: "Containers"
  },
  {
    label: "K8s CrashLoopBackOff",
    desc: "Pod Restart Cascade (Liveness probe failed HTTP 500)",
    log: "api-gateway-7f8d6-x9b12   0/1     CrashLoopBackOff   6          3m15s\nError: initialDelaySeconds exceeded, liveness probe failed HTTP 500",
    category: "Kubernetes"
  },
  {
    label: "Docker ECONNREFUSED",
    desc: "Database connection failed before container was ready",
    log: "Error: connect ECONNREFUSED 127.0.0.1:5432\n    at TCPConnectWrap.afterConnect [as oncomplete] (node:net:1494:16)\n    errno: -4078, code: 'ECONNREFUSED', syscall: 'connect', address: '127.0.0.1', port: 5432\nContext: App started before DB container was ready in docker-compose.",
    category: "Networking"
  },
  {
    label: "Python RecursionError",
    desc: "Maximum call stack depth exceeded in AST traversal",
    log: "RecursionError: maximum recursion depth exceeded while calling a Python object\n  File \"engine/parser.py\", line 84, in traverse_ast\n    return traverse_ast(node.child)\n  [Previous line repeated 996 more times]",
    category: "Python"
  },
  {
    label: "Postgres 53300 Connection Pool",
    desc: "Max client saturation in postgresql.conf",
    log: "psycopg2.OperationalError: FATAL: sorry, too many clients already (SQLSTATE 53300)",
    category: "Database"
  },
  {
    label: "Ambiguous Edge Case",
    desc: "Low grounding confidence (~41%) fallback test",
    log: "Application randomly stopped responding. No stack trace was written to stdout. Screen flickered and task disappeared from process list without error code.",
    category: "Diagnostic Fallback",
    isFailureDemo: true
  }
];

export default function LogInput({
  logText,
  setLogText,
  forceRefresh,
  setForceRefresh,
  onDiagnose,
  isLoading,
}) {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState(PRESETS[0]);
  const [isDragging, setIsDragging] = useState(false);
  const dropdownRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Keyboard shortcut: Cmd/Ctrl + Enter to trigger diagnosis
  const handleKeyDown = (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      if (!isLoading && logText.trim()) {
        onDiagnose();
      }
    }
  };

  // Line numbers calculation
  const linesCount = Math.max(logText.split("\n").length, 8);
  const lineNumbers = Array.from({ length: linesCount }, (_, i) => i + 1);

  // Detect error tokens for severity badges
  const detectedSeverity = (() => {
    const textUpper = logText.toUpperCase();
    if (textUpper.includes("FATAL") || textUpper.includes("OOMKILLED") || textUpper.includes("CRASHLOOPBACKOFF") || textUpper.includes("0X80070005")) {
      return { type: "error", label: "FATAL / ERROR" };
    }
    if (textUpper.includes("ERROR") || textUpper.includes("EXCEPTION") || textUpper.includes("ECONNREFUSED")) {
      return { type: "error", label: "ERROR" };
    }
    if (textUpper.includes("WARN")) {
      return { type: "warn", label: "WARNING" };
    }
    return null;
  })();

  // Drag and drop log file handling
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        if (event.target?.result) {
          setLogText(event.target.result);
        }
      };
      reader.readAsText(file);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        if (event.target?.result) {
          setLogText(event.target.result);
        }
      };
      reader.readAsText(file);
    }
  };

  return (
    <div className="panel-container log-input-panel">
      {/* Panel Header */}
      <div className="panel-header">
        <div className="panel-title-wrap">
          <span className="panel-index-badge">01</span>
          <h3>Input Error Log</h3>
        </div>
        <span className="panel-header-desc">Terminal Output & Traces</span>
      </div>

      <div className="log-panel-body">
        {/* Preset Selector Dropdown */}
        <div className="preset-selector-bar" ref={dropdownRef}>
          <div className="field-label-row">
            <span className="field-label">
              <SlidersIcon size={12} /> Failure Presets
            </span>
          </div>

          <div className="preset-dropdown-container">
            <button
              type="button"
              className="preset-trigger-btn"
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              aria-haspopup="true"
              aria-expanded={isDropdownOpen}
            >
              <div>
                <span className="preset-trigger-label">{selectedPreset.label}</span>
                <span className="preset-trigger-desc">({selectedPreset.category})</span>
              </div>
              <ChevronDownIcon size={14} />
            </button>

            {isDropdownOpen && (
              <div className="preset-menu-popover">
                {PRESETS.map((p, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="preset-option-item"
                    onClick={() => {
                      setSelectedPreset(p);
                      setLogText(p.log);
                      setIsDropdownOpen(false);
                    }}
                  >
                    <div className="preset-opt-title-row">
                      <span className="preset-opt-name">{p.label}</span>
                      {p.isFailureDemo && <span className="preset-opt-badge">Low Conf Test</span>}
                    </div>
                    <span className="preset-opt-desc">{p.desc}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Terminal / Code Editor */}
        <div
          className={`terminal-editor-wrapper ${isDragging ? 'dragging-active' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div className="terminal-editor-header">
            <div className="terminal-header-title">
              <TerminalIcon size={13} />
              <span>raw_stacktrace.log</span>
            </div>

            <div className="detected-tags-row">
              {detectedSeverity && (
                <span className={`severity-pill ${detectedSeverity.type}`}>
                  {detectedSeverity.label}
                </span>
              )}
            </div>
          </div>

          <div className="terminal-editor-body">
            {/* Line Number Gutter */}
            <div className="gutter-lines" aria-hidden="true">
              {lineNumbers.map((num) => (
                <div key={num}>{num}</div>
              ))}
            </div>

            {/* Editor Textarea */}
            <textarea
              ref={textareaRef}
              id="raw-log-input"
              className="code-textarea"
              placeholder="Paste terminal error logs, stack traces, exit codes, or drop a .log file..."
              value={logText}
              onChange={(e) => setLogText(e.target.value)}
              onKeyDown={handleKeyDown}
              spellCheck="false"
            />
          </div>

          <div className="dropzone-hint">
            <span>Drag & drop .log or .txt file</span>
            <button
              type="button"
              className="dropzone-file-btn"
              onClick={() => fileInputRef.current?.click()}
            >
              <FileUpIcon size={12} /> Browse file
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".log,.txt"
              style={{ display: 'none' }}
              onChange={handleFileSelect}
            />
          </div>
        </div>

        {/* Action Footer */}
        <div className="log-action-footer">
          <div className="cache-toggle-row">
            <label className="cache-toggle-label">
              <input
                type="checkbox"
                checked={forceRefresh}
                onChange={(e) => setForceRefresh(e.target.checked)}
              />
              <span>Bypass Semantic Cache</span>
            </label>
            <span className="cache-toggle-hint">
              {forceRefresh ? "Forcing live LLM inference" : "Sub-10ms cache active"}
            </span>
          </div>

          <button
            type="button"
            className="btn-primary-diagnose"
            onClick={onDiagnose}
            disabled={isLoading || !logText.trim()}
          >
            {isLoading ? (
              <>
                <ZapIcon size={14} className="spinner-icon" />
                <span>Executing Pipeline...</span>
              </>
            ) : (
              <>
                <ZapIcon size={14} />
                <span>Execute Diagnosis</span>
                <kbd>↵</kbd>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
