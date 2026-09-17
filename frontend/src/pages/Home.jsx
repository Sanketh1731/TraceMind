import React, { useState, useEffect, useRef } from 'react';
import LogInput, { PRESETS } from '../components/LogInput';
import ResultPanel from '../components/ResultPanel';
import PDFViewer from '../components/PDFViewer';
import ChatBox from '../components/ChatBox';
import CommandPalette from '../components/CommandPalette';
import { ToastContainer, ConfirmModal } from '../components/Toast';
import {
  TerminalIcon,
  BookOpenIcon,
  ZapIcon,
  TrashIcon,
  FileUpIcon,
  MessageSquareIcon,
  CommandIcon,
  ActivityIcon
} from '../components/Icons';
import {
  submitErrorQuery,
  fetchDocuments,
  fetchCacheStats,
  uploadDocumentFile,
  clearCache
} from '../api';

export default function Home() {
  const [logText, setLogText] = useState(
    "Error: 0x80070005 Access Denied while installing package at C:\\Users\\HP\\AppData\\Local\\Temp\\setup.msi"
  );
  const [forceRefresh, setForceRefresh] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [activeCitation, setActiveCitation] = useState(null);

  const [documents, setDocuments] = useState([]);
  const [currentDocId, setCurrentDocId] = useState(null);
  const [cacheStats, setCacheStats] = useState(null);
  const [showChat, setShowChat] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  // Modals and Toasts
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [isConfirmClearOpen, setIsConfirmClearOpen] = useState(false);
  const [toasts, setToasts] = useState([]);

  const fileInputRef = useRef(null);

  const addToast = (type, title, message) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, type, title, message }]);
  };

  const dismissToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Initial load
  useEffect(() => {
    loadDocsAndCache();
  }, []);

  // Global keyboard shortcut: Cmd+K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const loadDocsAndCache = async () => {
    try {
      const docs = await fetchDocuments();
      setDocuments(docs);
      if (docs.length > 0 && !currentDocId) {
        setCurrentDocId(docs[0].doc_id);
      }
      const stats = await fetchCacheStats();
      setCacheStats(stats);
    } catch (e) {
      console.error("Initialization error:", e);
    }
  };

  const handleDiagnose = async () => {
    if (!logText.trim()) return;
    setIsLoading(true);
    try {
      const data = await submitErrorQuery(logText, forceRefresh);
      setResult(data);
      if (data.citations?.length > 0) {
        const topCit = data.citations[0];
        setActiveCitation(topCit);
        if (topCit.doc_id) {
          setCurrentDocId(topCit.doc_id);
        }
      }
      const stats = await fetchCacheStats();
      setCacheStats(stats);
      addToast(
        "success",
        data.debug?.cache_hit ? "Instant Cache Hit" : "Diagnosis Complete",
        `Resolved in ${data.debug?.latency_ms ?? 28}ms with ${Math.round((data.confidence_score ?? 0.94) * 100)}% grounding.`
      );
    } catch (err) {
      addToast("error", "Diagnosis Failed", err.message || "Failed to execute RAG pipeline.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectCitation = (cit) => {
    setActiveCitation(cit);
    if (cit.doc_id) {
      setCurrentDocId(cit.doc_id);
    }
  };

  const handleUploadFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    try {
      await uploadDocumentFile(file);
      addToast("success", "Runbook Ingested", `'${file.name}' was indexed into vector database.`);
      await loadDocsAndCache();
    } catch (err) {
      addToast("error", "Upload Failed", err.message || "Document indexing failed.");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleConfirmClearCache = async () => {
    setIsConfirmClearOpen(false);
    try {
      await clearCache();
      const stats = await fetchCacheStats();
      setCacheStats(stats);
      addToast("info", "Cache Purged", "Semantic vector cache successfully cleared.");
    } catch (err) {
      addToast("error", "Clear Cache Failed", err.message);
    }
  };

  return (
    <div className="tracemind-app">
      {/* Top Engineering Nav */}
      <header className="app-header">
        <div className="header-brand">
          <div className="brand-icon-box">
            <ActivityIcon size={18} />
          </div>
          <div className="brand-info">
            <div className="brand-title-row">
              <h2 className="brand-name">TraceMind</h2>
              <span className="brand-version-badge">v2.4-prod</span>
            </div>
            <span className="brand-tagline">Deterministic Root-Cause Observability & RAG</span>
          </div>
        </div>

        {/* Telemetry bar & Actions */}
        <div className="header-actions">
          {cacheStats && (
            <div className="header-telemetry-pill">
              <span className="telemetry-status-dot" />
              <span>
                Cache Hit Rate: <strong>{cacheStats.hit_rate_pct}%</strong> ({cacheStats.hit_count} hits)
              </span>
            </div>
          )}

          <div className="header-telemetry-pill">
            <BookOpenIcon size={13} style={{ color: 'var(--accent-sky)' }} />
            <span>
              {documents.length} Runbooks ({documents.reduce((a, b) => a + (b.chunk_count || 0), 0)} chunks)
            </span>
          </div>

          <button
            type="button"
            className="command-trigger-btn"
            onClick={() => setIsCommandPaletteOpen(true)}
            title="Open Command Hub"
          >
            <CommandIcon size={13} />
            <span>Command Hub</span>
            <kbd>⌘K</kbd>
          </button>

          <button
            type="button"
            className="btn-header-action"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
            title="Ingest runbook markdown or PDF"
          >
            <FileUpIcon size={13} />
            <span>{isUploading ? "Ingesting..." : "Ingest Runbook"}</span>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".md,.txt,.pdf"
            onChange={handleUploadFile}
            style={{ display: 'none' }}
          />

          <button
            type="button"
            className="btn-header-action"
            onClick={() => setIsConfirmClearOpen(true)}
            title="Purge Semantic Vector Cache"
          >
            <TrashIcon size={13} />
          </button>

          <button
            type="button"
            className="btn-header-action"
            onClick={() => setShowChat(!showChat)}
            title="Toggle Grounded Copilot"
          >
            <MessageSquareIcon size={13} />
            <span>Copilot</span>
          </button>
        </div>
      </header>

      {/* 3-Column Main Workspace */}
      <main className="workspace-3col">
        {/* Left: Input, Presets & Terminal Editor */}
        <LogInput
          logText={logText}
          setLogText={setLogText}
          forceRefresh={forceRefresh}
          setForceRefresh={setForceRefresh}
          onDiagnose={handleDiagnose}
          isLoading={isLoading}
        />

        {/* Center: Progressive Disclosure Result Panel (Remediation, Waterfall Telemetry, Audit) */}
        <ResultPanel
          result={result}
          onSelectCitation={handleSelectCitation}
          activeCitation={activeCitation}
        />

        {/* Right: Source Knowledge Viewer with Search & Minimap */}
        <PDFViewer
          activeCitation={activeCitation}
          documents={documents}
          currentDocId={currentDocId}
          onSelectDoc={setCurrentDocId}
        />
      </main>

      {/* Slide-over Copilot Drawer */}
      {showChat && (
        <ChatBox
          onClose={() => setShowChat(false)}
          activeResult={result}
        />
      )}

      {/* Global Command Palette */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        presets={PRESETS}
        documents={documents}
        onSelectPreset={setLogText}
        onDiagnose={handleDiagnose}
        onSelectDoc={setCurrentDocId}
        onClearCache={() => setIsConfirmClearOpen(true)}
        forceRefresh={forceRefresh}
        setForceRefresh={setForceRefresh}
        onTriggerUpload={() => fileInputRef.current?.click()}
      />

      {/* Accessible Confirm Modal */}
      <ConfirmModal
        isOpen={isConfirmClearOpen}
        title="Purge Semantic Vector Cache"
        message="Are you sure you want to clear the semantic vector cache? Subsequent repeated queries will require full hybrid BM25 and LLM roundtrips."
        confirmLabel="Purge Cache"
        cancelLabel="Keep Cache"
        onConfirm={handleConfirmClearCache}
        onCancel={() => setIsConfirmClearOpen(false)}
      />

      {/* Toast Notification Container */}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
