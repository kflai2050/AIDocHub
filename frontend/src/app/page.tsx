"use client";

import React, { useState, useEffect, useRef } from "react";

interface DocumentItem {
  file_id: string;
  filename: string;
  type: string;
  path: string;
  content_preview: string;
  size: number;
}

interface SourceChunk {
  filename: string;
  chunk_index: number;
  document: string;
  score: number;
}

interface QueryResponse {
  answer: string;
  sources: SourceChunk[];
}

export default function Home() {
  const [groqKey, setGroqKey] = useState<string>("");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [uploading, setUploading] = useState<boolean>(false);
  const [indexingCancelled, setIndexingCancelled] = useState<boolean>(false);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  
  // Query states
  const [query, setQuery] = useState<string>("");
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [querying, setQuerying] = useState<boolean>(false);
  const [progressPct, setProgressPct] = useState<number>(0);
  const [progressText, setProgressText] = useState<string>("");

  // Preview states
  const [activePreview, setActivePreview] = useState<DocumentItem | null>(null);
  const [previewData, setPreviewData] = useState<any>(null);
  const [activeSheet, setActiveSheet] = useState<string>("");
  const [loadingPreview, setLoadingPreview] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const cancelUploadRef = useRef<boolean>(false);

  // Set default Groq key on mount
  useEffect(() => {
    const savedKey = localStorage.getItem("groq_api_key") || "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";
    setGroqKey(savedKey);
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const res = await fetch("http://localhost:8000/api/documents");
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (e) {
      console.error("Error fetching documents:", e);
    }
  };

  const saveApiKey = (key: string) => {
    setGroqKey(key);
    localStorage.setItem("groq_api_key", key);
  };

  const triggerUpload = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const filesArray = Array.from(e.target.files);
      processUploadQueue(filesArray);
    }
  };

  const processUploadQueue = async (files: File[]) => {
    setUploading(true);
    setIndexingCancelled(false);
    cancelUploadRef.current = false;
    setProgressPct(0);
    setProgressText("Preparing upload queue...");

    const newDocs: DocumentItem[] = [];

    for (let i = 0; i < files.length; i++) {
      if (cancelUploadRef.current) {
        setIndexingCancelled(true);
        setProgressText("Indexing cancelled by user.");
        break;
      }

      const file = files[i];
      setProgressText(`Processing (${i + 1}/${files.length}): ${file.name}...`);
      setProgressPct(Math.round((i / files.length) * 100));

      const formData = new FormData();
      formData.append("file", file);
      if (groqKey) {
        formData.append("groq_key", groqKey);
      }

      try {
        const res = await fetch("http://localhost:8000/api/upload", {
          method: "POST",
          body: formData,
        });

        if (res.ok) {
          const doc: DocumentItem = await res.json();
          newDocs.push(doc);
        } else {
          console.error(`Failed to upload ${file.name}`);
        }
      } catch (err) {
        console.error(`Error uploading ${file.name}:`, err);
      }
    }

    setProgressPct(100);
    setProgressText(cancelUploadRef.current ? "Indexing cancelled." : "All files successfully indexed!");
    
    // Refresh registry
    await fetchDocuments();
    
    // Reset file input
    if (fileInputRef.current) fileInputRef.current.value = "";
    
    setTimeout(() => {
      setUploading(false);
      setProgressPct(0);
      setProgressText("");
    }, 2000);
  };

  const cancelIndexing = () => {
    cancelUploadRef.current = true;
    setIndexingCancelled(true);
    setProgressText("Cancelling upload registry processing...");
  };

  const handleDelete = async (fileId: string) => {
    if (!confirm("Are you sure you want to delete and de-index this document?")) return;
    try {
      const res = await fetch(`http://localhost:8000/api/documents/${fileId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        // Clear active preview if deleted
        if (activePreview?.file_id === fileId) {
          setActivePreview(null);
          setPreviewData(null);
        }
        fetchDocuments();
      }
    } catch (e) {
      console.error("Error deleting document:", e);
    }
  };

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setQuerying(true);
    setProgressPct(10);
    setProgressText("Initializing request...");

    // Stage 1: Querying DB
    setTimeout(() => {
      setProgressPct(35);
      setProgressText("Querying ChromaDB vector database...");
    }, 400);

    // Stage 2: Synthesis
    setTimeout(async () => {
      setProgressPct(65);
      setProgressText("Synthesizing response via Groq (llama-3.3-70b-versatile)...");
      
      try {
        const res = await fetch("http://localhost:8000/api/query", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            query: query,
            groq_key: groqKey || null,
          }),
        });

        if (res.ok) {
          const data: QueryResponse = await res.json();
          setResponse(data);
          setProgressPct(100);
          setProgressText("Synthesized successfully!");
        } else {
          setResponse({
            answer: "Error: Failed to fetch synthesized response from server.",
            sources: [],
          });
          setProgressPct(100);
          setProgressText("Request failed.");
        }
      } catch (err) {
        console.error("Error querying backend:", err);
        setResponse({
          answer: "Network Error: Could not connect to the backend server.",
          sources: [],
        });
        setProgressPct(100);
        setProgressText("Network error.");
      } finally {
        setQuerying(false);
      }
    }, 1000);
  };

  const handlePreview = async (doc: DocumentItem) => {
    setActivePreview(doc);
    setLoadingPreview(true);
    setPreviewData(null);
    setActiveSheet("");

    try {
      const res = await fetch(`http://localhost:8000/api/preview/${doc.file_id}`);
      if (res.ok) {
        const data = await res.json();
        setPreviewData(data);
        if (data.type === "excel") {
          const sheetNames = Object.keys(data.sheets);
          if (sheetNames.length > 0) {
            setActiveSheet(sheetNames[0]);
          }
        }
      }
    } catch (e) {
      console.error("Error loading preview:", e);
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleReset = async () => {
    if (!confirm("Are you sure you want to clear the vector database and all uploaded files?")) return;
    try {
      const res = await fetch("http://localhost:8000/api/reset", {
        method: "POST",
      });
      if (res.ok) {
        setActivePreview(null);
        setPreviewData(null);
        setResponse(null);
        fetchDocuments();
      }
    } catch (e) {
      console.error("Error resetting database:", e);
    }
  };

  const parseMarkdown = (text: string) => {
    if (!text) return "";
    let html = text.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/^\s*-\s+(.*?)$/gm, '<li class="ml-5 list-disc text-slate-300 my-1">$1</li>');
    html = html.replace(/\n/g, "<br/>");
    return <div className="leading-relaxed text-slate-200" dangerouslySetInnerHTML={{ __html: html }} />;
  };

  const formatSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  const getBadgeClass = (type: string) => {
    const t = type.toUpperCase();
    if (t === "PDF") return "badge-pdf";
    if (t === "DOCX") return "badge-docx";
    if (t === "TXT") return "badge-txt";
    if (t === "XLS" || t === "XLSX") return "badge-excel";
    return "badge-image";
  };

  return (
    <main className="max-w-[1600px] mx-auto px-4 py-8 md:px-8">
      {/* Top Gradient Banner Header */}
      <header className="flex flex-col md:flex-row items-center justify-between gap-6 mb-10 pb-6 border-b border-slate-800/60">
        <div className="flex items-center gap-4">
          <div className="h-12 w-12 rounded-xl bg-gradient-to-tr from-purple-600 to-pink-500 flex items-center justify-center shadow-lg shadow-purple-900/30">
            <span className="text-2xl">📄</span>
          </div>
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight font-display gradient-text">
              AIDocHub
            </h1>
            <p className="text-sm text-slate-400 font-sans">
              AI Document Intelligence & Vector Assistant (Next.js + Groq)
            </p>
          </div>
        </div>

        {/* Global Groq API Key sidebar configuration */}
        <div className="w-full md:w-auto glass-panel p-4 rounded-xl flex flex-col sm:flex-row items-center gap-3">
          <label className="text-xs font-semibold text-slate-400 tracking-wider uppercase whitespace-nowrap">
            🔑 Groq API Key:
          </label>
          <input
            type="password"
            value={groqKey}
            onChange={(e) => saveApiKey(e.target.value)}
            placeholder="gsk_..."
            className="w-full sm:w-80 glass-input text-xs font-mono py-2 px-3 border border-slate-700/50"
          />
        </div>
      </header>

      {/* Grid Dashboard */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        {/* Left Column - Document Actions & Library */}
        <div className="space-y-8">
          {/* File Upload Zone */}
          <div className="glass-panel p-6 rounded-2xl relative overflow-hidden">
            <div className="absolute top-0 right-0 h-40 w-40 bg-purple-500/10 rounded-full blur-3xl -z-10" />
            <h3 className="text-lg font-bold text-slate-200 mb-4 flex items-center gap-2 font-display">
              <span>📥</span> Upload Documents
            </h3>
            
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              multiple
              className="hidden"
              accept=".txt,.pdf,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.gif,.webp"
            />

            <div
              onClick={triggerUpload}
              className="border-2 border-dashed border-slate-800 hover:border-purple-500/60 bg-slate-900/20 hover:bg-slate-900/40 py-10 rounded-xl cursor-pointer flex flex-col items-center justify-center text-center transition-all duration-300"
            >
              <div className="h-14 w-14 rounded-full bg-slate-800/50 flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform">
                📤
              </div>
              <p className="text-sm font-semibold text-slate-300">
                Click to browse files or drag them here
              </p>
              <p className="text-xs text-slate-500 mt-1">
                Supports TXT, PDF, DOCX, XLS/XLSX, PNG, JPG, WEBP, GIF
              </p>
            </div>

            {/* Uploading Progress */}
            {uploading && (
              <div className="mt-6 p-4 rounded-xl bg-slate-900/40 border border-slate-800/80">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-400 mb-2">
                  <span>{progressText}</span>
                  <span>{progressPct}%</span>
                </div>
                <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden mb-3">
                  <div
                    className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
                {!indexingCancelled && (
                  <button
                    onClick={cancelIndexing}
                    className="w-full py-2 text-xs font-bold text-red-400 hover:text-white bg-red-950/20 hover:bg-red-900/40 border border-red-900/30 hover:border-red-500/50 rounded-lg transition-colors"
                  >
                    🚫 Cancel Processing
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Document Library List */}
          <div className="glass-panel p-6 rounded-2xl">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-bold text-slate-200 flex items-center gap-2 font-display">
                <span>📂</span> Document Library
              </h3>
              {documents.length > 0 && (
                <button
                  onClick={handleReset}
                  className="py-1 px-3 text-xs font-semibold text-red-400 hover:text-white bg-red-950/10 hover:bg-red-900/30 border border-red-900/30 hover:border-red-500/40 rounded-lg transition-colors"
                >
                  🧹 Clear Database
                </button>
              )}
            </div>

            {documents.length === 0 ? (
              <div className="py-12 text-center text-slate-500 border border-dashed border-slate-800/40 rounded-xl bg-slate-950/10">
                <span className="text-3xl block mb-2">📭</span>
                No documents uploaded yet.
              </div>
            ) : (
              <div className="space-y-4 max-h-[480px] overflow-y-auto pr-2">
                {documents.map((doc) => (
                  <div
                    key={doc.file_id}
                    className="p-4 rounded-xl border border-slate-800/60 bg-slate-900/10 flex flex-col gap-3"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider ${getBadgeClass(doc.type)}`}>
                          {doc.type}
                        </span>
                        <strong className="text-sm font-semibold text-slate-300 truncate">
                          {doc.filename}
                        </strong>
                      </div>
                      <span className="text-xs text-slate-500 whitespace-nowrap">
                        {formatSize(doc.size)}
                      </span>
                    </div>

                    <div className="grid grid-cols-3 gap-2 mt-1">
                      <button
                        onClick={() => handlePreview(doc)}
                        className="py-1.5 px-2 text-xs font-semibold text-purple-400 hover:text-white bg-purple-950/10 hover:bg-purple-900/30 border border-purple-900/30 hover:border-purple-500/40 rounded-lg transition-colors flex items-center justify-center gap-1"
                      >
                        🔍 Preview
                      </button>
                      
                      <a
                        href={`http://localhost:8000/api/download/${doc.file_id}`}
                        download
                        className="py-1.5 px-2 text-xs font-semibold text-blue-400 hover:text-white bg-blue-950/10 hover:bg-blue-900/30 border border-blue-900/30 hover:border-blue-500/40 rounded-lg transition-colors flex items-center justify-center gap-1"
                      >
                        📥 Download
                      </a>

                      <button
                        onClick={() => handleDelete(doc.file_id)}
                        className="py-1.5 px-2 text-xs font-semibold text-red-400 hover:text-white bg-red-950/10 hover:bg-red-900/30 border border-red-900/30 hover:border-red-500/40 rounded-lg transition-colors flex items-center justify-center gap-1"
                      >
                        🗑️ Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Active Preview Panel */}
          {activePreview && (
            <div className="glass-panel p-6 rounded-2xl relative overflow-hidden">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-slate-200 flex items-center gap-2">
                  🔎 Preview: {activePreview.filename}
                </h3>
                <button
                  onClick={() => {
                    setActivePreview(null);
                    setPreviewData(null);
                  }}
                  className="h-6 w-6 rounded-full bg-slate-800 hover:bg-slate-700 flex items-center justify-center text-xs text-slate-400"
                >
                  ✕
                </button>
              </div>

              {loadingPreview ? (
                <div className="py-12 text-center text-xs text-slate-500">
                  Loading preview data...
                </div>
              ) : previewData ? (
                <div className="max-h-[500px] overflow-y-auto pr-2 mt-4 bg-slate-950/40 p-4 rounded-xl border border-slate-900">
                  {/* Excel Sheet Visual Render */}
                  {previewData.type === "excel" && (
                    <div className="space-y-4">
                      <div className="flex items-center gap-2 mb-3">
                        <label className="text-xs text-slate-400">Sheet:</label>
                        <select
                          value={activeSheet}
                          onChange={(e) => setActiveSheet(e.target.value)}
                          className="glass-input text-xs py-1 px-2 border border-slate-800"
                        >
                          {Object.keys(previewData.sheets).map((name) => (
                            <option key={name} value={name}>
                              {name}
                            </option>
                          ))}
                        </select>
                      </div>

                      {activeSheet && previewData.sheets[activeSheet] && (
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs text-left border-collapse border border-slate-850">
                            <thead>
                              <tr className="bg-slate-900">
                                {previewData.sheets[activeSheet].columns.map((col: string) => (
                                  <th key={col} className="p-2 border border-slate-800 font-bold text-slate-300">
                                    {col}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {previewData.sheets[activeSheet].rows.slice(0, 100).map((row: any, rIdx: number) => (
                                <tr key={rIdx} className="hover:bg-slate-900/50 transition-colors">
                                  {previewData.sheets[activeSheet].columns.map((col: string) => (
                                    <td key={col} className="p-2 border border-slate-800 text-slate-400">
                                      {String(row[col])}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          {previewData.sheets[activeSheet].rows.length > 100 && (
                            <div className="text-center text-[10px] text-slate-500 py-2">
                              Showing first 100 rows. Download full file to view complete dataset.
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Image Inline Preview */}
                  {previewData.type === "image" && (
                    <div className="space-y-4">
                      <img
                        src={`data:image/${previewData.format};base64,${previewData.base64}`}
                        alt={activePreview.filename}
                        className="max-h-[300px] w-auto mx-auto rounded border border-slate-800 object-contain"
                      />
                      <div className="text-xs font-mono text-slate-400 p-3 bg-slate-900/40 rounded border border-slate-900 mt-3 whitespace-pre-wrap leading-relaxed">
                        {activePreview.content_preview}
                      </div>
                    </div>
                  )}

                  {/* Text View */}
                  {previewData.type === "text" && (
                    <pre className="text-xs text-slate-300 whitespace-pre-wrap font-sans leading-relaxed">
                      {previewData.content}
                    </pre>
                  )}
                </div>
              ) : (
                <div className="py-6 text-center text-xs text-red-400">
                  Failed to load preview data.
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column - Chat Query Box */}
        <div className="space-y-8">
          <div className="glass-panel p-6 rounded-2xl relative">
            <div className="absolute top-0 right-0 h-40 w-40 bg-pink-500/10 rounded-full blur-3xl -z-10" />
            <h3 className="text-lg font-bold text-slate-200 mb-6 flex items-center gap-2 font-display">
              <span>💬</span> Ask Your Documents
            </h3>

            <form onSubmit={handleQuery} className="space-y-4">
              <div className="flex flex-col gap-2">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g. What are HCLTech's Gen AI assessment details? or What are the marks in Maths?"
                  className="w-full glass-input text-sm border border-slate-800"
                />
              </div>
              <button
                type="submit"
                disabled={querying || !query.trim()}
                className="w-full py-3 text-sm font-bold text-white bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-500 hover:to-pink-400 rounded-xl transition-all shadow-lg shadow-purple-900/20 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none"
              >
                {querying ? "🔍 Processing..." : "🚀 Submit Query"}
              </button>
            </form>

            {/* Query step-by-step progress logging */}
            {querying && (
              <div className="mt-6 p-4 rounded-xl bg-slate-900/30 border border-slate-900">
                <div className="flex items-center justify-between text-xs text-slate-400 mb-2 font-semibold">
                  <span>{progressText}</span>
                  <span>{progressPct}%</span>
                </div>
                <div className="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-purple-500 to-pink-500 h-1.5 rounded-full transition-all duration-300"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
              </div>
            )}

            {/* AI Agent Response */}
            {response && (
              <div className="mt-8 space-y-6 pt-6 border-t border-slate-800/80">
                <div>
                  <h4 className="text-xs font-bold text-purple-400 tracking-wider uppercase mb-3 flex items-center gap-2">
                    <span>🤖</span> Agent Response
                  </h4>
                  <div className="p-4 rounded-xl bg-purple-950/10 border border-purple-900/30 text-sm font-medium">
                    {parseMarkdown(response.answer)}
                  </div>
                </div>

                {/* Retrieved Source Match Chunks */}
                {response.sources && response.sources.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold text-pink-400 tracking-wider uppercase mb-3 flex items-center gap-2">
                      <span>📚</span> Retrieved Sources (ChromaDB)
                    </h4>
                    <div className="space-y-3 max-h-[350px] overflow-y-auto pr-2">
                      {response.sources.map((source, sIdx) => {
                        const pct = Math.round(source.score * 100);
                        const progressStyle = { width: `${pct > 0 ? pct : 0}%` };
                        return (
                          <div key={sIdx} className="source-chunk-card flex flex-col gap-2">
                            <div className="flex items-center justify-between text-xs gap-3">
                              <span className="font-semibold text-slate-300 truncate">
                                File: {source.filename} (Chunk {source.chunk_index})
                              </span>
                              <span className="score-badge whitespace-nowrap">
                                {pct}% Similarity
                              </span>
                            </div>
                            
                            {/* Similarity visualization progress bar */}
                            <div className="w-full bg-slate-950 rounded-full h-1 overflow-hidden">
                              <div
                                className="bg-gradient-to-r from-purple-500 to-pink-500 h-1 rounded-full"
                                style={progressStyle}
                              />
                            </div>

                            <p className="text-xs text-slate-400 leading-relaxed font-sans italic mt-1">
                              "{source.document}"
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
