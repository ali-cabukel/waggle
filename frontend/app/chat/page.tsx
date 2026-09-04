"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { Send, Wifi, WifiOff } from "lucide-react";
import { CLIENT_API_KEY, WS_URL } from "@/lib/api";

type ChatMsg = {
  role: "user" | "assistant" | "tool" | "system";
  content: string;
};

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMsg[]>([
    {
      role: "system",
      content: "Ask about scraped products (cheapest travel book) or news (latest BBC headlines).",
    },
  ]);
  const [input, setInput] = useState("");
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const assistantRef = useRef("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const url = `${WS_URL}?api_key=${encodeURIComponent(CLIENT_API_KEY)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (event) => {
      const payload = JSON.parse(event.data) as {
        type: string;
        content?: string;
        name?: string;
        phase?: string;
      };
      if (payload.type === "ready") {
        return;
      }
      if (payload.type === "token") {
        assistantRef.current += payload.content || "";
        const text = assistantRef.current;
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (last?.role === "assistant") {
            next[next.length - 1] = { role: "assistant", content: text };
          } else {
            next.push({ role: "assistant", content: text });
          }
          return next;
        });
      } else if (payload.type === "tool") {
        setMessages((prev) => [
          ...prev,
          {
            role: "tool",
            content: `${payload.name} ${payload.phase || ""}`.trim(),
          },
        ]);
      } else if (payload.type === "final") {
        assistantRef.current = "";
      } else if (payload.type === "error") {
        setMessages((prev) => [
          ...prev,
          { role: "system", content: payload.content || "Error" },
        ]);
        assistantRef.current = "";
      }
    };
    return () => ws.close();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function send(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    assistantRef.current = "";
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    wsRef.current.send(JSON.stringify({ type: "user", content: text }));
    setInput("");
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-3xl flex-col">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold">Chat</h1>
          <p className="text-sm text-stone-600">WebSocket query agent over Mongo products and articles.</p>
        </div>
        <span className="inline-flex items-center gap-1 text-sm text-stone-600">
          {connected ? (
            <>
              <Wifi className="h-4 w-4 text-emerald-600" /> Connected
            </>
          ) : (
            <>
              <WifiOff className="h-4 w-4 text-red-600" /> Disconnected
            </>
          )}
        </span>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto rounded-xl border border-stone-200 bg-white p-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
              msg.role === "user"
                ? "ml-auto bg-honey-600 text-white"
                : msg.role === "tool"
                  ? "bg-stone-100 font-mono text-xs text-stone-600"
                  : msg.role === "system"
                    ? "bg-honey-50 text-honey-800"
                    : "bg-stone-100 text-stone-900"
            }`}
          >
            <pre className="whitespace-pre-wrap font-sans">{msg.content}</pre>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <form onSubmit={send} className="mt-3 flex gap-2">
        <input
          className="flex-1 rounded-lg border border-stone-200 px-3 py-2 text-sm"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="What's the cheapest travel book?"
        />
        <button
          type="submit"
          disabled={!connected}
          className="inline-flex items-center gap-2 rounded-lg bg-honey-600 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          <Send className="h-4 w-4" />
          Send
        </button>
      </form>
    </div>
  );
}
