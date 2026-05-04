"use client";

import { useState, useEffect, useCallback } from "react";
import { Thread } from "@/components/assistant-ui/thread";
import {
  AssistantRuntimeProvider,
  useAui,
  AuiProvider,
  Suggestions,
} from "@assistant-ui/react";
import {
  useChatRuntime,
  AssistantChatTransport,
} from "@assistant-ui/react-ai-sdk";

type Customer = {
  customer_id: string;
  name: string;
  loyalty_tier: string;
};

type TraceChunk = {
  chunk_id: string;
  domain: string;
  score: number;
  source: string;
  product_id: string | null;
  category: string | null;
  policy_type: string | null;
  text_preview: string;
};

type TraceData = {
  intent_classification: {
    domains: Record<string, number>;
    primary_domain: string;
    is_ambiguous: boolean;
    is_multi_domain: boolean;
  };
  hyde_activated: boolean;
  hyde_hypothetical: string | null;
  scope_decision: {
    is_in_scope: boolean;
    reason: string;
    uncertainty_note: string | null;
  } | null;
  decomposed_queries: { text: string; target_domain: string }[] | null;
  chunks_retrieved: number;
  chunks: TraceChunk[];
  faithfulness_score: number | null;
  faithfulness?: {
    score: number;
    total_claims: number;
    unsupported_claims: number;
    regeneration_triggered: boolean;
  };
  latency_ms: number;
  stage_latencies: Record<string, number>;
  error?: string;
  answerability?: {
    answerable: boolean;
    action: string;
    reason: string;
    missing_evidence: string[];
  } | null;
  evidence_claims?: {
    claim: string;
    evidence_type: string;
    source_id: string | null;
    supported: boolean;
    risk_level: string;
  }[];
};

function ThreadWithSuggestions() {
  const aui = useAui({
    suggestions: Suggestions([
      {
        title: "What's the return policy",
        label: "for sale items?",
        prompt: "What's the return policy for sale items?",
      },
      {
        title: "Compare Airlift and Airbrush",
        label: "fabric types",
        prompt:
          "What's the difference between Airlift and Airbrush fabric?",
      },
      {
        title: "What are the loyalty tiers",
        label: "and their benefits?",
        prompt:
          "What are the ALO Access loyalty tiers and what benefits does each tier get?",
      },
    ]),
  });
  return (
    <AuiProvider value={aui}>
      <Thread />
    </AuiProvider>
  );
}

function TracePanel({
  trace,
  isOpen,
  onToggle,
}: {
  trace: TraceData | null;
  isOpen: boolean;
  onToggle: () => void;
}) {
  if (!trace) return null;

  const intent = trace.intent_classification;
  const sortedDomains = Object.entries(intent.domains).sort(
    ([, a], [, b]) => b - a
  );

  return (
    <div className="border-t bg-muted/30">
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between px-6 py-2 text-sm font-medium hover:bg-muted/50 transition-colors"
      >
        <span className="flex items-center gap-2">
          🔍 Pipeline Trace
          <span className="text-xs text-muted-foreground">
            {trace.latency_ms}ms · {trace.chunks_retrieved} chunks ·{" "}
            {intent.primary_domain}
          </span>
        </span>
        <span className="text-muted-foreground">{isOpen ? "▼" : "▶"}</span>
      </button>

      {isOpen && (
        <div className="max-h-[50vh] overflow-y-auto px-6 pb-4 text-sm space-y-4">
          {/* Intent Classification */}
          <div>
            <h4 className="font-semibold mb-1">Intent Classification</h4>
            <div className="space-y-1">
              {sortedDomains.map(([domain, score]) => (
                <div key={domain} className="flex items-center gap-2">
                  <span className="w-16 text-muted-foreground">{domain}</span>
                  <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-foreground/60 rounded-full"
                      style={{ width: `${score * 100}%` }}
                    />
                  </div>
                  <span className="w-10 text-right text-muted-foreground">
                    {(score * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
            <div className="mt-1 text-xs text-muted-foreground">
              {intent.is_ambiguous && "⚠️ Ambiguous "}
              {intent.is_multi_domain && "🔀 Multi-domain"}
            </div>
          </div>

          {/* Pipeline Decisions */}
          <div>
            <h4 className="font-semibold mb-1">Pipeline Decisions</h4>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              <span className="text-muted-foreground">HyDE activated:</span>
              <span>{trace.hyde_activated ? "✅ Yes" : "❌ No"}</span>
              <span className="text-muted-foreground">Scope guard:</span>
              <span>
                {trace.scope_decision
                  ? trace.scope_decision.is_in_scope
                    ? "✅ In scope"
                    : "❌ Out of scope"
                  : "— Not triggered"}
              </span>
              <span className="text-muted-foreground">Decomposed:</span>
              <span>
                {trace.decomposed_queries
                  ? `${trace.decomposed_queries.length} sub-queries`
                  : "— Single query"}
              </span>
              <span className="text-muted-foreground">Faithfulness:</span>
              <span>
                {trace.faithfulness_score != null
                  ? `${(trace.faithfulness_score * 100).toFixed(0)}%`
                  : "N/A"}
                {trace.faithfulness?.regeneration_triggered &&
                  " (regenerated)"}
              </span>
              {trace.answerability && (
              <>
                <span className="text-muted-foreground">Answerability:</span>
                <span>
                  {trace.answerability.answerable
                    ? "✅ Answerable"
                    : `⚠️ ${trace.answerability.action}`}
                </span>
              </>
            )}
            </div>
          </div>

          {/* Stage Latencies */}
          <div>
            <h4 className="font-semibold mb-1">Stage Latencies</h4>
            <div className="space-y-0.5 text-xs">
              {Object.entries(trace.stage_latencies)
                .sort(([, a], [, b]) => b - a)
                .map(([stage, ms]) => (
                  <div key={stage} className="flex items-center gap-2">
                    <span className="w-40 text-muted-foreground">
                      {stage.replace(/_/g, " ")}
                    </span>
                    <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-foreground/40 rounded-full"
                        style={{
                          width: `${Math.min(
                            (ms / trace.latency_ms) * 100,
                            100
                          )}%`,
                        }}
                      />
                    </div>
                    <span className="w-16 text-right text-muted-foreground">
                      {ms.toFixed(0)}ms
                    </span>
                  </div>
                ))}
              <div className="flex items-center gap-2 font-medium pt-1 border-t">
                <span className="w-40">Total</span>
                <div className="flex-1" />
                <span className="w-16 text-right">
                  {trace.latency_ms.toFixed(0)}ms
                </span>
              </div>
            </div>
          </div>

          {/* Retrieved Chunks */}
          <div>
            <h4 className="font-semibold mb-1">
              Retrieved Chunks ({trace.chunks.length})
            </h4>
            <div className="space-y-2">
              {trace.chunks.map((chunk, i) => (
                <div
                  key={chunk.chunk_id}
                  className="rounded border bg-background p-2 text-xs"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono font-medium">
                      {i + 1}. {chunk.chunk_id}
                    </span>
                    <span className="text-muted-foreground">
                      {chunk.domain} · {chunk.score.toFixed(4)} ·{" "}
                      {chunk.source}
                    </span>
                  </div>
                  <p className="text-muted-foreground line-clamp-2">
                    {chunk.text_preview}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* HyDE Hypothetical */}
          {trace.hyde_hypothetical && (
            <div>
              <h4 className="font-semibold mb-1">HyDE Hypothetical Document</h4>
              <p className="text-xs text-muted-foreground bg-background rounded border p-2">
                {trace.hyde_hypothetical}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function Home() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<string>("");
  const [trace, setTrace] = useState<TraceData | null>(null);
  const [traceOpen, setTraceOpen] = useState(false);

  useEffect(() => {
    fetch("http://localhost:8000/api/customers")
      .then((res) => res.json())
      .then((data) => setCustomers(data.customers || []))
      .catch(() => setCustomers([]));
  }, []);

  // Poll for trace data after messages change
  const fetchTrace = useCallback(() => {
    fetch("http://localhost:8000/api/trace")
      .then((res) => res.json())
      .then((data) => {
        if (data.trace) {
          setTrace(data.trace);
        }
      })
      .catch(() => {});
  }, []);

  // Poll for trace updates periodically when a message might be in flight
  useEffect(() => {
    const interval = setInterval(() => {
      fetchTrace();
    }, 3000);
    return () => clearInterval(interval);
  }, [fetchTrace]);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <header className="flex items-center justify-between border-b px-6 py-3">
        <div className="flex items-center gap-3">
          <span className="text-2xl font-bold tracking-widest">ALO</span>
          <span className="text-sm text-muted-foreground">
            Yoga Assistant
          </span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <label
              htmlFor="customer-select"
              className="text-sm text-muted-foreground"
            >
              Signed in as:
            </label>
            <select
              id="customer-select"
              value={selectedCustomer}
              onChange={(e) => {
                setSelectedCustomer(e.target.value);
                setTrace(null);
              }}
              className="rounded-md border bg-background px-3 py-1.5 text-sm"
            >
              <option value="">No customer (general query)</option>
              {customers.map((c) => (
                <option key={c.customer_id} value={c.customer_id}>
                  {c.name} ({c.loyalty_tier})
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={() => {
              fetchTrace();
              setTraceOpen(!traceOpen);
            }}
            className={`rounded-md border px-3 py-1.5 text-sm transition-colors ${
              traceOpen
                ? "bg-foreground text-background"
                : "hover:bg-muted"
            }`}
          >
            🔍 Trace
          </button>
        </div>
      </header>

      {/* Chat — keyed by customer so the runtime hook re-initialises on switch */}
      <ChatSession
        key={`runtime-${selectedCustomer}`}
        selectedCustomer={selectedCustomer}
      />

      {/* Trace Panel */}
      <TracePanel
        trace={trace}
        isOpen={traceOpen}
        onToggle={() => setTraceOpen(!traceOpen)}
      />
    </div>
  );
}

/**
 * Inner component that owns the chat runtime.
 * Keyed by selectedCustomer in the parent so React fully remounts it
 * (and re-runs useChatRuntime) whenever the customer changes.
 */
function ChatSession({ selectedCustomer }: { selectedCustomer: string }) {
  const runtime = useChatRuntime({
    transport: new AssistantChatTransport({
      api: "/api/chat",
      body: selectedCustomer ? { customer_id: selectedCustomer } : undefined,
    }),
  });

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <div className="flex-1 overflow-hidden">
        <ThreadWithSuggestions />
      </div>
    </AssistantRuntimeProvider>
  );
}
