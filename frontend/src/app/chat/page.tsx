"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authService, chatService, documentService } from "@/lib/api";
import { Citation, Conversation, DocumentItem, QueryResponse } from "@/types";
import {
  BookOpen,
  FileText,
  Loader2,
  MessageSquare,
  Send,
  Sparkles,
} from "lucide-react";

interface ChatMessageUI {
  id: string;
  sender: "user" | "assistant";
  content: string;
  citations?: Citation[];
  latency_ms?: number;
}

function ChatWorkspace() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialDocId = searchParams.get("docId") || "";

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>(initialDocId);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [messages, setMessages] = useState<ChatMessageUI[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authService.isAuthenticated()) {
      router.push("/login");
      return;
    }
    documentService
      .list(1, 50)
      .then((res) => {
        const indexed = res.items.filter((d) => d.status === "indexed");
        setDocuments(indexed);
      })
      .catch(() => setError("Failed to load indexed documents."));
  }, [router]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    const userText = query.trim();
    setQuery("");
    setError(null);
    setMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, sender: "user", content: userText },
    ]);
    setLoading(true);

    try {
      const resp: QueryResponse = await chatService.query({
        query: userText,
        conversation_id: conversationId,
        document_id: selectedDocId || undefined,
      });
      setConversationId(resp.conversation_id);
      setMessages((prev) => [
        ...prev,
        {
          id: resp.message_id,
          sender: "assistant",
          content: resp.answer,
          citations: resp.citations,
          latency_ms: resp.latency_ms,
        },
      ]);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Query failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-6xl flex-col px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex flex-col gap-3 border-b border-gray-800 pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center space-x-2">
          <MessageSquare className="h-5 w-5 text-blue-400" />
          <h1 className="text-xl font-bold text-white">Document Q&A (Baseline A: Text RAG)</h1>
        </div>
        <div className="flex items-center space-x-2">
          <label className="text-xs text-gray-400">Scope:</label>
          <select
            value={selectedDocId}
            onChange={(e) => {
              setSelectedDocId(e.target.value);
              setConversationId(undefined);
              setMessages([]);
            }}
            className="rounded-lg border border-gray-700 bg-surface px-3 py-1.5 text-xs text-gray-200 focus:border-blue-500 focus:outline-none"
          >
            <option value="">All Indexed Workspace Documents</option>
            {documents.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.filename} ({doc.page_count}p)
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-400">
          {error}
        </div>
      )}

      <div className="my-4 flex-1 space-y-4 overflow-y-auto pr-2">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center text-gray-500">
            <Sparkles className="mb-3 h-10 w-10 text-blue-500/60" />
            <p className="text-sm font-medium text-gray-300">Ask a question about your uploaded PDFs</p>
            <p className="mt-1 max-w-md text-xs text-gray-500">
              Retrieves top-K text chunks from Qdrant and synthesizes grounded answers with page-level citations.
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-3xl rounded-2xl px-4 py-3 text-sm ${
                  msg.sender === "user"
                    ? "bg-blue-600 text-white"
                    : "border border-gray-800 bg-surface text-gray-200"
                }`}
              >
                <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>

                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 border-t border-gray-800 pt-2">
                    <p className="mb-1.5 flex items-center space-x-1 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
                      <BookOpen className="h-3 w-3 text-blue-400" />
                      <span>Retrieved Citations ({msg.citations.length})</span>
                      {msg.latency_ms !== undefined && (
                        <span className="ml-auto font-normal text-gray-500">{msg.latency_ms} ms</span>
                      )}
                    </p>
                    <div className="space-y-1.5">
                      {msg.citations.map((cit, idx) => (
                        <div
                          key={`${msg.id}-cit-${idx}`}
                          className="rounded-lg border border-gray-800 bg-background/60 p-2 text-xs"
                        >
                          <div className="flex items-center space-x-2 font-medium text-blue-400">
                            <FileText className="h-3 w-3" />
                            <span>
                              {cit.document_name} — Page {cit.page_number}
                            </span>
                          </div>
                          <p className="mt-1 line-clamp-2 text-[11px] text-gray-400">{cit.snippet}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex items-center space-x-2 text-xs text-gray-400">
            <Loader2 className="h-4 w-4 animate-spin text-blue-400" />
            <span>Retrieving evidence and generating grounded answer...</span>
          </div>
        )}
      </div>

      <form onSubmit={handleSend} className="flex items-center space-x-2 border-t border-gray-800 pt-4">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question about your documents..."
          className="flex-1 rounded-xl border border-gray-700 bg-surface px-4 py-3 text-sm text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="flex items-center space-x-2 rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:opacity-50"
        >
          <Send className="h-4 w-4" />
          <span>Ask</span>
        </button>
      </form>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-sm text-gray-400">Loading chat...</div>}>
      <ChatWorkspace />
    </Suspense>
  );
}

