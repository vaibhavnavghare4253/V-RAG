import Link from "next/link";
import { ArrowRight, BarChart2, CheckCircle, Database, Eye, FileSearch, Layers, ShieldAlert, Sparkles } from "lucide-react";

export default function HomePage() {
  return (
    <div className="relative overflow-hidden">
      {/* Background Glow */}
      <div className="pointer-events-none absolute left-1/2 top-0 -translate-x-1/2 opacity-30">
        <div className="h-[450px] w-[800px] rounded-full bg-gradient-to-r from-blue-600/40 via-purple-600/40 to-cyan-500/30 blur-3xl" />
      </div>

      {/* Hero Section */}
      <section className="mx-auto max-w-7xl px-4 pt-20 pb-16 text-center sm:px-6 lg:px-8">
        <div className="inline-flex items-center space-x-2 rounded-full border border-blue-500/30 bg-blue-500/10 px-4 py-1.5 text-xs font-semibold text-blue-400">
          <Sparkles className="h-3.5 w-3.5" />
          <span>Research Platform: Adaptive Multimodal RAG with Uncertainty Awareness</span>
        </div>

        <h1 className="mt-8 text-4xl font-extrabold tracking-tight sm:text-6xl">
          Intelligent Document Q&A with <br />
          <span className="bg-gradient-to-r from-blue-400 via-indigo-300 to-purple-400 bg-clip-text text-transparent">
            Calibrated Uncertainty & Abstention
          </span>
        </h1>

        <p className="mx-auto mt-6 max-w-3xl text-lg text-gray-400">
          AdaptiveDocAI doesn&apos;t just search text. It dynamically routes queries across paragraphs, complex tables, charts, figures, and scans—evaluating evidence sufficiency and abstaining when information is unverified or incomplete.
        </p>

        <div className="mt-10 flex items-center justify-center space-x-4">
          <Link
            href="/register"
            className="flex items-center space-x-2 rounded-lg bg-blue-600 px-6 py-3 text-base font-semibold text-white shadow-lg shadow-blue-500/25 transition hover:bg-blue-500"
          >
            <span>Launch Dashboard</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/login"
            className="rounded-lg border border-gray-700 bg-surface px-6 py-3 text-base font-semibold text-gray-300 transition hover:bg-surfaceLight hover:text-white"
          >
            Sign In
          </Link>
        </div>
      </section>

      {/* Key Architecture Pillars */}
      <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
          <div className="rounded-xl border border-gray-800 bg-surface/50 p-6 backdrop-blur">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
              <Layers className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-lg font-bold text-white">Adaptive Modality Routing</h3>
            <p className="mt-2 text-sm text-gray-400">
              Dispatches dynamic search strategies across text chunks, table data, and high-res vector figures based on question intent.
            </p>
          </div>

          <div className="rounded-xl border border-gray-800 bg-surface/50 p-6 backdrop-blur">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-purple-500/10 text-purple-400">
              <ShieldAlert className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-lg font-bold text-white">Multi-Factor Uncertainty</h3>
            <p className="mt-2 text-sm text-gray-400">
              Quantifies relevance, evidence coverage, claim entailment, and modality completeness to reliably abstain on ambiguous questions.
            </p>
          </div>

          <div className="rounded-xl border border-gray-800 bg-surface/50 p-6 backdrop-blur">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-cyan-500/10 text-cyan-400">
              <BarChart2 className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-lg font-bold text-white">4-Baseline Comparative Rigor</h3>
            <p className="mt-2 text-sm text-gray-400">
              Built to evaluate Baseline A (Text RAG), Baseline B (Fixed Multimodal), Baseline C (Adaptive RAG), and our Proposed architecture.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

