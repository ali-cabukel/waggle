"use client";

import { useEffect, useState } from "react";
import { Play, Plus, RefreshCw } from "lucide-react";
import {
  createScraper,
  fetchArticles,
  fetchProducts,
  fetchRuns,
  fetchScrapers,
  fetchStats,
  runScraper,
  type Article,
  type Product,
  type Run,
  type Scraper,
} from "@/lib/api";
import { RunDrawer } from "@/components/RunDrawer";

export default function DashboardPage() {
  const [scrapers, setScrapers] = useState<Scraper[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [articles, setArticles] = useState<Article[]>([]);
  const [totalProducts, setTotalProducts] = useState(0);
  const [totalArticles, setTotalArticles] = useState(0);
  const [stats, setStats] = useState<{ total: number; in_stock: number } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<Run | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  async function load() {
    try {
      const [s, r, p, a, st] = await Promise.all([
        fetchScrapers(),
        fetchRuns(),
        fetchProducts(),
        fetchArticles(),
        fetchStats(),
      ]);
      setScrapers(s.scrapers);
      setRuns(r.runs);
      setProducts(p.products);
      setTotalProducts(p.total);
      setArticles(a.articles);
      setTotalArticles(a.total);
      setStats({ total: st.total, in_stock: st.in_stock });
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    }
  }

  useEffect(() => {
    load();
    const id = setInterval(load, 4000);
    return () => clearInterval(id);
  }, []);

  async function handleRun(id: string, trigger: "on_demand" | "agentic") {
    setBusyId(id);
    try {
      await runScraper(id, trigger);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Run failed");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Scrapers</h1>
          <p className="mt-1 text-stone-600">
            Run books or news scrapers, then query products and headlines in Chat.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={load}
            className="inline-flex items-center gap-2 rounded-lg border border-stone-200 bg-white px-3 py-2 text-sm hover:bg-stone-50"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-honey-600 px-3 py-2 text-sm text-white hover:bg-honey-800"
          >
            <Plus className="h-4 w-4" />
            New scraper
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="Scrapers" value={String(scrapers.length)} />
        <Stat label="Products" value={String(stats?.total ?? totalProducts)} />
        <Stat label="Articles" value={String(totalArticles)} />
        <Stat label="In stock" value={String(stats?.in_stock ?? "—")} />
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </div>
      )}

      <section className="overflow-hidden rounded-xl border border-stone-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-stone-50 text-stone-500">
            <tr>
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Engine</th>
              <th className="px-4 py-3 font-medium">Schedule</th>
              <th className="px-4 py-3 font-medium">Last run</th>
              <th className="px-4 py-3 font-medium">Items</th>
              <th className="px-4 py-3 font-medium" />
            </tr>
          </thead>
          <tbody>
            {scrapers.map((scraper) => (
              <tr key={scraper.id} className="border-t border-stone-100">
                <td className="px-4 py-3">
                  <div className="font-medium">{scraper.name}</div>
                  <div className="text-xs text-stone-500">{scraper.start_url}</div>
                  <div className="mt-1 text-xs capitalize text-stone-400">
                    {scraper.item_kind || "product"}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className="rounded-full bg-honey-50 px-2 py-0.5 text-xs text-honey-800">
                    {scraper.engine}
                  </span>
                  <span className="ml-2 text-xs text-stone-500">{scraper.mode}</span>
                </td>
                <td className="px-4 py-3 text-stone-600">
                  {scraper.schedule || "On demand"}
                </td>
                <td className="px-4 py-3">
                  {scraper.last_run ? (
                    <button
                      className="text-left"
                      onClick={() => setSelectedRun(scraper.last_run as Run)}
                    >
                      <StatusBadge status={scraper.last_run.status} />
                    </button>
                  ) : (
                    <span className="text-stone-400">Never</span>
                  )}
                </td>
                <td className="px-4 py-3">{scraper.item_count ?? scraper.product_count ?? 0}</td>
                <td className="px-4 py-3 text-right">
                  <button
                    disabled={busyId === scraper.id}
                    onClick={() => handleRun(scraper.id, "on_demand")}
                    className="mr-2 inline-flex items-center gap-1 rounded-md bg-stone-900 px-2.5 py-1.5 text-xs text-white disabled:opacity-50"
                  >
                    <Play className="h-3 w-3" />
                    Run now
                  </button>
                  <button
                    disabled={busyId === scraper.id}
                    onClick={() => handleRun(scraper.id, "agentic")}
                    className="inline-flex items-center gap-1 rounded-md border border-stone-200 px-2.5 py-1.5 text-xs disabled:opacity-50"
                  >
                    Agentic
                  </button>
                </td>
              </tr>
            ))}
            {scrapers.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-stone-500">
                  No scrapers yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section>
          <h2 className="mb-3 text-lg font-medium">Recent runs</h2>
          <div className="overflow-hidden rounded-xl border border-stone-200 bg-white">
            <ul className="divide-y divide-stone-100 text-sm">
              {runs.slice(0, 8).map((run) => (
                <li key={run.id}>
                  <button
                    className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-stone-50"
                    onClick={() => setSelectedRun(run)}
                  >
                    <span>{run.scraper_name || run.scraper_id}</span>
                    <span className="flex items-center gap-3 text-stone-500">
                      {run.items_count} items
                      <StatusBadge status={run.status} />
                    </span>
                  </button>
                </li>
              ))}
              {runs.length === 0 && (
                <li className="px-4 py-6 text-stone-500">No runs yet.</li>
              )}
            </ul>
          </div>
        </section>
        <section>
          <h2 className="mb-3 text-lg font-medium">
            Products <span className="text-stone-400">({totalProducts})</span>
          </h2>
          <div className="overflow-hidden rounded-xl border border-stone-200 bg-white">
            <ul className="divide-y divide-stone-100 text-sm">
              {products.slice(0, 8).map((p) => (
                <li key={p.id} className="flex items-center justify-between px-4 py-3">
                  <div>
                    <div className="font-medium">{p.title}</div>
                    <div className="text-xs text-stone-500">
                      {p.category} · {p.rating ?? "?"}★ · {p.availability}
                    </div>
                  </div>
                  <div className="text-stone-700">
                    {p.price != null ? `£${p.price}` : "—"}
                  </div>
                </li>
              ))}
              {products.length === 0 && (
                <li className="px-4 py-6 text-stone-500">
                  Run a scraper to populate Mongo.
                </li>
              )}
            </ul>
          </div>
        </section>
      </div>

      <section>
        <h2 className="mb-3 text-lg font-medium">
          Articles <span className="text-stone-400">({totalArticles})</span>
        </h2>
        <div className="overflow-hidden rounded-xl border border-stone-200 bg-white">
          <ul className="divide-y divide-stone-100 text-sm">
            {articles.slice(0, 10).map((article) => (
              <li key={article.id} className="px-4 py-3">
                <div className="font-medium">{article.title}</div>
                <div className="text-xs text-stone-500">
                  {article.source} · {article.category}
                  {article.published_at ? ` · ${article.published_at}` : ""}
                </div>
                {article.summary && (
                  <p className="mt-1 line-clamp-2 text-xs text-stone-600">{article.summary}</p>
                )}
              </li>
            ))}
            {articles.length === 0 && (
              <li className="px-4 py-6 text-stone-500">
                Run BBC News, NBC News, or Wikipedia to populate headlines.
              </li>
            )}
          </ul>
        </div>
      </section>

      {selectedRun && (
        <RunDrawer run={selectedRun} onClose={() => setSelectedRun(null)} />
      )}
      {showCreate && (
        <CreateModal
          onClose={() => setShowCreate(false)}
          onCreated={async () => {
            setShowCreate(false);
            await load();
          }}
        />
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-stone-200 bg-white px-4 py-5">
      <div className="text-sm text-stone-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const color =
    status === "success"
      ? "bg-emerald-50 text-emerald-800"
      : status === "failed"
        ? "bg-red-50 text-red-800"
        : status === "running"
          ? "bg-sky-50 text-sky-800"
          : "bg-stone-100 text-stone-600";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs capitalize ${color}`}>{status}</span>
  );
}

function CreateModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => Promise<void>;
}) {
  const [name, setName] = useState("Books to Scrape");
  const [url, setUrl] = useState("https://books.toscrape.com/");
  const [engine, setEngine] = useState("crawl4ai");
  const [mode, setMode] = useState("schema");
  const [itemKind, setItemKind] = useState<"product" | "article">("product");
  const [schedule, setSchedule] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await createScraper({
        name,
        start_url: url,
        engine,
        mode,
        item_kind: itemKind,
        schedule: schedule || undefined,
      });
      await onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 p-4">
      <form
        onSubmit={submit}
        className="w-full max-w-md space-y-3 rounded-xl bg-white p-6 shadow-xl"
      >
        <h2 className="text-lg font-semibold">New scraper</h2>
        <input
          className="w-full rounded-lg border px-3 py-2 text-sm"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name"
          required
        />
        <input
          className="w-full rounded-lg border px-3 py-2 text-sm"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Start URL"
          required
        />
        <div className="grid grid-cols-2 gap-2">
          <select
            className="rounded-lg border px-3 py-2 text-sm"
            value={engine}
            onChange={(e) => setEngine(e.target.value)}
          >
            <option value="crawl4ai">crawl4ai</option>
            <option value="playwright">playwright</option>
            <option value="obscura">obscura</option>
          </select>
          <select
            className="rounded-lg border px-3 py-2 text-sm"
            value={mode}
            onChange={(e) => setMode(e.target.value)}
          >
            <option value="schema">schema</option>
            <option value="agentic">agentic</option>
          </select>
        </div>
        <select
          className="w-full rounded-lg border px-3 py-2 text-sm"
          value={itemKind}
          onChange={(e) => setItemKind(e.target.value as "product" | "article")}
        >
          <option value="product">product (ecommerce)</option>
          <option value="article">article (news listing)</option>
        </select>
        <input
          className="w-full rounded-lg border px-3 py-2 text-sm"
          value={schedule}
          onChange={(e) => setSchedule(e.target.value)}
          placeholder="Cron (optional, e.g. 0 */6 * * *)"
        />
        {error && <p className="text-sm text-red-700">{error}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-lg px-3 py-2 text-sm">
            Cancel
          </button>
          <button
            disabled={busy}
            className="rounded-lg bg-honey-600 px-3 py-2 text-sm text-white"
          >
            Create
          </button>
        </div>
      </form>
    </div>
  );
}
