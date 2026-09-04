const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_WAGGLE_API_KEY || "waggle-dev-key";

export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api/v1/ws/chat";
export const CLIENT_API_KEY = API_KEY;

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("X-API-Key", API_KEY);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${API_URL}${path}`, { ...init, headers, cache: "no-store" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export type LastRun = {
  id: string;
  status: string;
  items_count: number;
  error?: string | null;
  started_at?: string;
  finished_at?: string;
  trigger?: string;
  engine?: string;
  events?: Array<Record<string, unknown>>;
};

export type Scraper = {
  id: string;
  name: string;
  slug: string;
  start_url: string;
  extra_urls?: string[];
  engine: string;
  mode: string;
  schedule?: string | null;
  enabled: boolean;
  max_pages: number;
  instructions?: string;
  last_run?: LastRun | null;
  item_kind?: "product" | "article";
  item_count?: number;
  product_count?: number;
};

export type Run = LastRun & {
  scraper_id: string;
  scraper_name?: string;
  duration_ms?: number | null;
};

export type Product = {
  id: string;
  title: string;
  price: number | null;
  currency: string;
  rating: number | null;
  availability: string;
  category: string;
  image_url?: string | null;
  source_url: string;
  source: string;
};

export type Article = {
  id: string;
  title: string;
  summary?: string | null;
  author?: string | null;
  category: string;
  published_at?: string | null;
  source_url: string;
  source: string;
};

export async function fetchScrapers() {
  return request<{ scrapers: Scraper[] }>("/api/v1/scrapers");
}

export async function fetchRuns(scraperId?: string) {
  const q = scraperId ? `?scraper_id=${scraperId}` : "";
  return request<{ runs: Run[] }>(`/api/v1/runs${q}`);
}

export async function fetchRun(id: string) {
  return request<{ run: Run }>(`/api/v1/runs/${id}`);
}

export async function fetchProducts(params?: { q?: string; category?: string }) {
  const search = new URLSearchParams();
  if (params?.q) search.set("q", params.q);
  if (params?.category) search.set("category", params.category);
  const q = search.toString() ? `?${search}` : "";
  return request<{ products: Product[]; total: number }>(`/api/v1/products${q}`);
}

export async function fetchArticles(params?: { q?: string; category?: string; source?: string }) {
  const search = new URLSearchParams();
  if (params?.q) search.set("q", params.q);
  if (params?.category) search.set("category", params.category);
  if (params?.source) search.set("source", params.source);
  const q = search.toString() ? `?${search}` : "";
  return request<{ articles: Article[]; total: number }>(`/api/v1/articles${q}`);
}

export async function fetchArticleStats() {
  return request<{
    total: number;
    sources: Array<{ source: string; count: number }>;
    categories: Array<{ category: string; count: number }>;
  }>("/api/v1/articles/stats");
}

export async function fetchStats() {
  return request<{
    total: number;
    in_stock: number;
    categories: Array<{ category: string; count: number; avg_price: number | null }>;
    cheapest: Product | null;
  }>("/api/v1/products/stats");
}

export async function runScraper(id: string, trigger: "on_demand" | "agentic" = "on_demand") {
  return request<{ ok: boolean; status: string }>(`/api/v1/scrapers/${id}/run`, {
    method: "POST",
    body: JSON.stringify({ trigger }),
  });
}

export async function createScraper(body: {
  name: string;
  start_url: string;
  engine: string;
  mode: string;
  item_kind?: "product" | "article";
  schedule?: string;
  instructions?: string;
}) {
  return request<{ scraper: Scraper }>("/api/v1/scrapers", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
