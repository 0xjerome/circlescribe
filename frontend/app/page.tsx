"use client";
import { useState } from "react";

type Report = {status:string;entries:Array<{event_id:string;event_type:string;amount:number;currency:string;source_text:string}>;exceptions:Array<{code:string;message:string}>;superseded_event_ids:string[]};
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home(){
  const [report,setReport]=useState<Report|null>(null); const [loading,setLoading]=useState(false); const [error,setError]=useState("");
  async function runDemo(){setLoading(true);setError("");try{const r=await fetch(`${API}/api/v1/demo/reconcile`,{method:"POST"});if(!r.ok)throw new Error(`API returned ${r.status}`);setReport(await r.json());}catch(e){setError(e instanceof Error?e.message:"Unable to reach API");}finally{setLoading(false)}}
  return <main>
    <section className="hero"><div className="eyebrow">AWS Agents for Humans · Good Neighbor Agents</div><h1>CircleScribe</h1><p className="lede">Turn community savings-group meetings into verified records and follow-up work.</p><div className="principle"><strong>AI interprets language.</strong><strong>Deterministic code validates money.</strong><strong>Humans resolve ambiguity.</strong></div></section>
    <section className="panel"><div><div className="step">Deterministic correction demo</div><h2>“Thirty thousand… actually, make that twenty.”</h2><p>The original event is superseded instead of being counted as a second contribution.</p></div><button onClick={runDemo} disabled={loading}>{loading?"Reconciling…":"Run reconciliation"}</button></section>
    {error&&<section className="error">{error}</section>}
    {report&&<section className="results"><div className="metric"><span>Status</span><strong>{report.status}</strong></div><div className="metric"><span>Accepted entries</span><strong>{report.entries.length}</strong></div><div className="metric"><span>Superseded</span><strong>{report.superseded_event_ids.length}</strong></div><div className="metric"><span>Review items</span><strong>{report.exceptions.length}</strong></div><div className="card full"><h3>Accepted ledger result</h3>{report.entries.map(e=><div className="entry" key={e.event_id}><div><strong>{e.event_type}</strong><p>{e.source_text}</p></div><strong>{e.amount.toLocaleString()} {e.currency}</strong></div>)}</div></section>}
  </main>
}
