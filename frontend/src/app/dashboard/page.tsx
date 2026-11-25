"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { authService, documentService } from "@/lib/api";
import { DocumentItem, DocumentStatus } from "@/types";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle,
  Clock,
  FileText,
  FileUp,
  Loader2,
  MessageSquare,
  RefreshCw,
  Trash2,
  UploadCloud,
} from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  useEffect(() => {
    if (!authService.isAuthenticated()) {
      router.push("/login");
      return;
    }
    fetchDocuments();
  }, [router]);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const res = await documentService.list();
      setDocuments(res.items);
    } catch (err: any) {
      setError("Failed to load documents.");
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are supported.");
      return;
    }
    setError(null);
    setSuccessMsg(null);
    setUploading(true);
    setUploadProgress(0);

    try {
      const res = await documentService.upload(file, (pct) => setUploadProgress(pct));
      setSuccessMsg(`Document "${file.name}" uploaded successfully and queued for indexing.`);
      await fetchDocuments();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Upload failed.");
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDelete = async (docId: string, filename: string) => {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) return;
    try {
      await documentService.delete(docId);
      setDocuments(documents.filter((d) => d.id !== docId));
      setSuccessMsg(`Document "${filename}" deleted.`);
    } catch (err) {
      setError("Failed to delete document.");
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const getStatusBadge = (status: DocumentStatus) => {
    switch (status) {
      case "indexed":
        return (
          <span className="inline-flex items-center space-x-1.5 rounded-full bg-green-500/10 px-2.5 py-0.5 text-xs font-medium text-green-400 border border-green-500/20">
            <CheckCircle className="h-3 w-3" />
            <span>Indexed</span>
          </span>
        );
      case "processing":
        return (
          <span className="inline-flex items-center space-x-1.5 rounded-full bg-blue-500/10 px-2.5 py-0.5 text-xs font-medium text-blue-400 border border-blue-500/20">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>Processing</span>
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center space-x-1.5 rounded-full bg-red-500/10 px-2.5 py-0.5 text-xs font-medium text-red-400 border border-red-500/20">
            <AlertTriangle className="h-3 w-3" />
            <span>Failed</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1.5 rounded-full bg-yellow-500/10 px-2.5 py-0.5 text-xs font-medium text-yellow-400 border border-yellow-500/20">
            <Clock className="h-3 w-3" />
            <span>Pending</span>
          </span>
        );
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-6 border-b border-gray-800">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Document Library</h1>
          <p className="mt-1 text-sm text-gray-400">
            Upload multi-modal research papers and reports for adaptive retrieval
          </p>
        </div>
        <button
          onClick={fetchDocuments}
          className="mt-4 sm:mt-0 flex items-center space-x-2 rounded-lg border border-gray-800 bg-surface px-3 py-2 text-xs font-medium text-gray-300 hover:bg-surfaceLight transition"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Refresh</span>
        </button>
      </div>

      {/* Notifications */}
      {error && (
        <div className="mt-6 flex items-center space-x-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-400">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {successMsg && (
        <div className="mt-6 flex items-center space-x-2 rounded-lg border border-green-500/30 bg-green-500/10 p-3 text-sm text-green-400">
          <CheckCircle className="h-5 w-5 flex-shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Upload Dropzone */}
      <div className="mt-8">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragOver(false);
            if (e.dataTransfer.files?.[0]) {
              handleFileUpload(e.dataTransfer.files[0]);
            }
          }}
          onClick={() => fileInputRef.current?.click()}
          className={`cursor-pointer rounded-2xl border-2 border-dashed p-8 text-center transition ${isDragOver
              ? "border-blue-500 bg-blue-500/10"
              : "border-gray-800 bg-surface/40 hover:border-gray-700 hover:bg-surface/80"
            }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => {
              if (e.target.files?.[0]) handleFileUpload(e.target.files[0]);
            }}
            accept="application/pdf"
            className="hidden"
          />

          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400">
            {uploading ? (
              <Loader2 className="h-7 w-7 animate-spin" />
            ) : (
              <UploadCloud className="h-7 w-7" />
            )}
          </div>

          <h3 className="mt-4 text-base font-semibold text-white">
            {uploading ? "Uploading Document..." : "Click to upload or drag & drop"}
          </h3>
          <p className="mt-1 text-xs text-gray-400">
            Supported formats: PDF (Research papers, reports with tables, charts, figures up to 50MB)
          </p>

          {uploading && (
            <div className="mx-auto mt-4 w-64">
              <div className="h-1.5 w-full rounded-full bg-gray-800">
                <div
                  className="h-1.5 rounded-full bg-blue-500 transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="mt-1 text-xs text-blue-400">{uploadProgress}%</p>
            </div>
          )}
        </div>
      </div>

      {/* Document Table */}
      <div className="mt-10 overflow-hidden rounded-xl border border-gray-800 bg-surface/60">
        <div className="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Uploaded Documents ({documents.length})</h2>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16 text-gray-500 space-x-2">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>Loading document library...</span>
          </div>
        ) : documents.length === 0 ? (
          <div className="py-16 text-center text-gray-500">
            <FileText className="mx-auto h-10 w-10 text-gray-600 mb-2" />
            <p className="text-sm">No documents uploaded yet in this workspace.</p>
            <p className="text-xs text-gray-600 mt-1">Upload a research PDF above to start indexing.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-surfaceLight/50 text-xs uppercase text-gray-400">
                <tr>
                  <th className="px-6 py-3">Document Name</th>
                  <th className="px-6 py-3">Size</th>
                  <th className="px-6 py-3">Pages</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Uploaded</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800 text-gray-300">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-surfaceLight/30 transition">
                    <td className="px-6 py-4 font-medium text-white flex items-center space-x-3">
                      <FileText className="h-4 w-4 text-blue-400 flex-shrink-0" />
                      <span className="truncate max-w-xs sm:max-w-md">{doc.filename}</span>
                    </td>
                    <td className="px-6 py-4 text-gray-400">{formatBytes(doc.file_size_bytes)}</td>
                    <td className="px-6 py-4 text-gray-400">{doc.page_count || "-"}</td>
                    <td className="px-6 py-4">{getStatusBadge(doc.status)}</td>
                    <td className="px-6 py-4 text-xs text-gray-400">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                      <td className="px-6 py-4 text-right space-x-2">
                        {doc.status === "indexed" && (
                          <button
                            onClick={() => router.push(`/chat?docId=${doc.id}`)}
                            className="inline-flex items-center space-x-1 rounded px-2 py-1 text-xs font-medium text-blue-400 hover:bg-blue-500/10 transition"
                            title="Ask Questions"
                          >
                            <MessageSquare className="h-3.5 w-3.5" />
                            <span>Chat</span>
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(doc.id, doc.filename)}
                          className="rounded p-1 text-gray-400 hover:text-red-400 hover:bg-red-500/10 transition"
                          title="Delete Document"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

