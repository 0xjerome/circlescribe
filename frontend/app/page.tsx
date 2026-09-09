"use client";

import { useMemo, useState } from "react";

type Event = {
  id: string;
  event_type: string;
  member_id: string | null;
  amount_minor: number | null;
  currency: string | null;
  confidence: number;
  source_text: string;
  supersedes_event_id: string | null;
  note: string | null;
};

type ProcessResult = {
  mode: string;
  extraction: {
    meeting_summary: string;
    events: Event[];
  };
  reconciliation: {
    status: "reconciled" | "needs_review";
    entries: Array<{
      event_id: string;
      member_id: string | null;
      event_type: string;
      amount: number;
      currency: string;
      source_text: string;
    }>;
    exceptions: Array<{
      event_id: string;
      code: string;
      message: string;
      source_text: string;
    }>;
    superseded_event_ids: string[];
    totals_by_type: Record<string, number>;
  };
  generated_minutes: string;
};

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const CLEAN_TRANSCRIPT = `Chair: Welcome everyone. Amina is here, John is here, Mary is here and Sarah is here.
Amina: I paid fifty thousand for my savings contribution.
John: I paid thirty thousand.
Mary: I am repaying forty thousand on my loan.
Sarah: I would like to request a loan of one hundred thousand for one month.
John: Actually, correct my contribution. Make that twenty thousand, not thirty.
Chair: Noted. We will review Sarah's request before approving it.`;

const AMBIGUOUS_TRANSCRIPT = `Chair: Mary, can you confirm your contribution?
Mary: Maybe I paid fifty thousand, I am not sure.
Chair: We will check the receipt before recording the final amount.`;

function formatAmount(value: number | null, currency: string | null) {
  if (value == null) return "—";
  return `${value.toLocaleString()} ${currency ?? "UGX"}`;
}

export default function Home() {
  const [transcript, setTranscript] = useState(CLEAN_TRANSCRIPT);
  const [result, setResult] = useState<ProcessResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const acceptedTotal = useMemo(
    () => result?.reconciliation.entries.reduce((sum, entry) => sum + entry.amount, 0) ?? 0,
    [result]
  );

  async function processMeeting() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const response = await fetch(`${API}/api/v1/demo/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail ?? `API returned ${response.status}`);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to process meeting");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <header className="hero">
        <div className="eyebrow">AWS Agents for Humans · Good Neighbor Agents</div>
        <h1>CircleScribe</h1>
        <p className="lede">
          Turn a community savings-group meeting into verified records and follow-up work,
          while protecting every financial state change behind deterministic validation.
        </p>
        <div className="principle">
          <strong>AI interprets language</strong>
          <strong>Deterministic code validates money</strong>
          <strong>Humans resolve ambiguity</strong>
        </div>
      </header>

      <section className="notice">
        <strong>Local development mode</strong>
        <span>
          AWS account access is currently unavailable, so this screen uses a clearly labeled
          deterministic extraction adapter. The production endpoint remains Strands + Bedrock.
        </span>
      </section>

      <section className="workspace">
        <div className="editor">
          <div className="sectionHead">
            <div>
              <span className="step">Step 1</span>
              <h2>Meeting transcript</h2>
            </div>
            <div className="presets">
              <button className="ghost" onClick={() => setTranscript(CLEAN_TRANSCRIPT)}>
                Correction demo
              </button>
              <button className="ghost" onClick={() => setTranscript(AMBIGUOUS_TRANSCRIPT)}>
                Ambiguity demo
              </button>
            </div>
          </div>
          <textarea value={transcript} onChange={(e) => setTranscript(e.target.value)} />
          <button className="primary" onClick={processMeeting} disabled={loading || !transcript.trim()}>
            {loading ? "Processing meeting…" : "Process meeting"}
          </button>
        </div>

        <aside className="flow">
          <span className="step">Workflow</span>
          <ol>
            <li>Extract typed meeting events</li>
            <li>Resolve explicit corrections</li>
            <li>Validate ledger mutations</li>
            <li>Escalate genuine uncertainty</li>
            <li>Generate draft minutes</li>
          </ol>
        </aside>
      </section>

      {error && <section className="error">{error}</section>}

      {result && (
        <>
          <section className="metrics">
            <div className="metric">
              <span>Status</span>
              <strong>{result.reconciliation.status}</strong>
            </div>
            <div className="metric">
              <span>Events understood</span>
              <strong>{result.extraction.events.length}</strong>
            </div>
            <div className="metric">
              <span>Ledger entries</span>
              <strong>{result.reconciliation.entries.length}</strong>
            </div>
            <div className="metric">
              <span>Human review</span>
              <strong>{result.reconciliation.exceptions.length}</strong>
            </div>
            <div className="metric">
              <span>Accepted total</span>
              <strong>{acceptedTotal.toLocaleString()} UGX</strong>
            </div>
          </section>

          <section className="grid">
            <div className="card wide">
              <div className="sectionHead">
                <div>
                  <span className="step">Step 2</span>
                  <h2>Structured events</h2>
                </div>
                <span className="modeBadge">{result.mode}</span>
              </div>
              <div className="eventTable">
                {result.extraction.events.map((event) => (
                  <div className="eventRow" key={event.id}>
                    <div>
                      <strong>{event.event_type.replaceAll("_", " ")}</strong>
                      <p>{event.source_text}</p>
                    </div>
                    <div className="eventMeta">
                      <span>{formatAmount(event.amount_minor, event.currency)}</span>
                      <span>{Math.round(event.confidence * 100)}% confidence</span>
                      {event.supersedes_event_id && (
                        <span>replaces {event.supersedes_event_id}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="card">
              <span className="step">Step 3</span>
              <h2>Verified ledger</h2>
              {result.reconciliation.entries.length === 0 ? (
                <p className="muted">No ledger mutation was accepted.</p>
              ) : (
                result.reconciliation.entries.map((entry) => (
                  <div className="ledgerRow" key={entry.event_id}>
                    <div>
                      <strong>{entry.event_type.replaceAll("_", " ")}</strong>
                      <small>{entry.member_id ?? "group"}</small>
                    </div>
                    <strong>{entry.amount.toLocaleString()} {entry.currency}</strong>
                  </div>
                ))
              )}
            </div>

            <div className="card">
              <span className="step">Step 4</span>
              <h2>Human decisions</h2>
              {result.reconciliation.exceptions.length === 0 ? (
                <div className="successBox">No human review is required.</div>
              ) : (
                result.reconciliation.exceptions.map((item) => (
                  <div className="reviewBox" key={`${item.event_id}-${item.code}`}>
                    <strong>{item.code.replaceAll("_", " ")}</strong>
                    <p>{item.message}</p>
                    <small>{item.source_text}</small>
                  </div>
                ))
              )}
            </div>

            <div className="card wide">
              <span className="step">Step 5</span>
              <h2>Draft meeting minutes</h2>
              <pre>{result.generated_minutes}</pre>
            </div>
          </section>
        </>
      )}
    </main>
  );
}
