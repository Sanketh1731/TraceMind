import React, { useState, useEffect, useRef } from 'react';
import { fetchDocumentContent } from '../api';
import {
  BookOpenIcon,
  SearchIcon,
  XIcon,
  CheckCircleIcon,
  ChevronDownIcon
} from './Icons';

export default function PDFViewer({ activeCitation, documents, currentDocId, onSelectDoc }) {
  const [docContent, setDocContent] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const contentRef = useRef(null);

  // Load document content
  useEffect(() => {
    if (currentDocId) {
      fetchDocumentContent(currentDocId)
        .then((data) => setDocContent(data))
        .catch((err) => console.error("Error loading document:", err));
    }
  }, [currentDocId]);

  // Smooth scroll to active citation
  useEffect(() => {
    if (activeCitation && contentRef.current) {
      setTimeout(() => {
        const highlightedEl = contentRef.current.querySelector(".grounded-source-mark");
        if (highlightedEl) {
          highlightedEl.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }, 100);
    }
  }, [activeCitation, docContent]);

  // Compute citation match and count occurrences
  const renderHighlightedDoc = (rawText) => {
    if (!rawText) return null;

    let targetSnippet = activeCitation?.snippet?.trim() || "";
    let matchTarget = targetSnippet;

    if (targetSnippet && !rawText.includes(targetSnippet)) {
      const cleanPrefix = targetSnippet.slice(0, 45).trim();
      if (cleanPrefix && rawText.includes(cleanPrefix)) {
        matchTarget = cleanPrefix;
      }
    }

    // Split by citation if found
    if (matchTarget && rawText.includes(matchTarget)) {
      const parts = rawText.split(matchTarget);
      return parts.map((part, index) => (
        <React.Fragment key={index}>
          {renderTextWithSearch(part)}
          {index < parts.length - 1 && (
            <mark className="grounded-source-mark">
              {matchTarget}
            </mark>
          )}
        </React.Fragment>
      ));
    }

    return renderTextWithSearch(rawText);
  };

  const renderTextWithSearch = (textSegment) => {
    if (!searchTerm.trim() || !textSegment) return textSegment;

    const regex = new RegExp(`(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const parts = textSegment.split(regex);

    return parts.map((part, i) =>
      regex.test(part) ? (
        <mark key={i} className="search-match-mark">{part}</mark>
      ) : (
        part
      )
    );
  };

  // Search match count
  const searchMatchCount = (() => {
    if (!searchTerm.trim() || !docContent?.content) return 0;
    try {
      const regex = new RegExp(searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
      return (docContent.content.match(regex) || []).length;
    } catch {
      return 0;
    }
  })();

  return (
    <div className="panel-container doc-viewer-panel">
      {/* Panel Header */}
      <div className="panel-header">
        <div className="panel-title-wrap">
          <span className="panel-index-badge">03</span>
          <h3>Source Knowledge</h3>
        </div>

        <select
          className="doc-dropdown-selector"
          value={currentDocId || ""}
          onChange={(e) => onSelectDoc(e.target.value)}
        >
          {documents.map((d) => (
            <option key={d.doc_id} value={d.doc_id}>
              {d.title} ({d.chunk_count} chunks)
            </option>
          ))}
        </select>
      </div>

      {/* Search & Citation Status Toolbar */}
      <div className="viewer-search-toolbar">
        <div className="viewer-search-input-wrap">
          <SearchIcon size={13} style={{ color: 'var(--text-muted)' }} />
          <input
            type="text"
            placeholder="Search within this runbook..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          {searchTerm && (
            <>
              <span className="search-matches-counter">{searchMatchCount} found</span>
              <button
                type="button"
                onClick={() => setSearchTerm("")}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#64748b' }}
              >
                <XIcon size={12} />
              </button>
            </>
          )}
        </div>

        {activeCitation && (
          <div className="active-citation-status-pill">
            <CheckCircleIcon size={12} />
            <span>{activeCitation.page_or_section}</span>
          </div>
        )}
      </div>

      {/* Document Content View & Minimap Rail */}
      <div className="doc-viewer-canvas-wrap">
        <div className="doc-markdown-content" ref={contentRef}>
          {docContent ? (
            <>
              <div className="doc-header-banner">
                <h4>{docContent.title}</h4>
                <div className="doc-meta-tags">
                  <span>Format: {docContent.type?.toUpperCase()}</span>
                  <span>&bull;</span>
                  <span>ID: {docContent.doc_id}</span>
                </div>
              </div>

              <div style={{ whiteSpace: 'pre-wrap', fontFamily: 'var(--font-mono)', fontSize: '11px', lineHeight: 1.6 }}>
                {renderHighlightedDoc(docContent.content)}
              </div>
            </>
          ) : (
            <div style={{ padding: '30px', textAlign: 'center', color: '#64748b' }}>
              Loading runbook document...
            </div>
          )}
        </div>

        {/* Citation Minimap Rail */}
        <div className="citation-minimap-rail" title="Visual Citation Locator">
          {activeCitation && <div className="minimap-marker" style={{ top: '38%' }} />}
          {searchTerm && searchMatchCount > 0 && (
            <>
              <div className="minimap-marker" style={{ top: '22%', background: '#f59e0b' }} />
              <div className="minimap-marker" style={{ top: '65%', background: '#f59e0b' }} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
