const API_BASE = import.meta.env?.VITE_API_URL || "http://localhost:8000/api";

export async function submitErrorQuery(rawError, forceRefresh = false) {
  const response = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ raw_error: rawError, force_refresh: forceRefresh }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Network error" }));
    throw new Error(err.detail || "Query execution failed");
  }
  return response.json();
}

export async function fetchDocuments() {
  const response = await fetch(`${API_BASE}/documents`);
  if (!response.ok) throw new Error("Failed to load documents");
  return response.json();
}

export async function fetchDocumentContent(docId) {
  const response = await fetch(`${API_BASE}/documents/${docId}`);
  if (!response.ok) throw new Error("Failed to load document content");
  return response.json();
}

export async function fetchCacheStats() {
  const response = await fetch(`${API_BASE}/health/cache`);
  if (!response.ok) throw new Error("Failed to load cache stats");
  return response.json();
}

export async function clearCache() {
  const response = await fetch(`${API_BASE}/health/cache/clear`, { method: "POST" });
  return response.json();
}

export async function uploadDocumentFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE}/documents/upload`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) throw new Error("Upload failed");
  return response.json();
}
