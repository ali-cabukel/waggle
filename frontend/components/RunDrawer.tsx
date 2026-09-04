"use client";

import { X } from "lucide-react";
import type { Run } from "@/lib/api";

export function RunDrawer({ run, onClose }: { run: Run; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/30">
      <aside className="h-full w-full max-w-md overflow-y-auto bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Run</h2>
          <button onClick={onClose} aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>
        <dl className="space-y-2 text-sm">
          <Row label="Status" value={run.status} />
          <Row label="Engine" value={run.engine || "—"} />
          <Row label="Trigger" value={run.trigger || "—"} />
          <Row label="Items" value={String(run.items_count ?? 0)} />
          <Row label="Started" value={run.started_at || "—"} />
          <Row label="Finished" value={run.finished_at || "—"} />
          {run.error && <Row label="Error" value={run.error} />}
        </dl>
        {run.events && run.events.length > 0 && (
          <div className="mt-6">
            <h3 className="mb-2 text-sm font-medium">Events</h3>
            <ul className="space-y-2 text-xs text-stone-600">
              {run.events.map((event, i) => (
                <li key={i} className="rounded-lg bg-stone-50 p-2 font-mono">
                  {JSON.stringify(event)}
                </li>
              ))}
            </ul>
          </div>
        )}
      </aside>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-stone-500">{label}</dt>
      <dd className="break-words font-medium">{value}</dd>
    </div>
  );
}
