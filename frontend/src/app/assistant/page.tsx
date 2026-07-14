"use client";

import { useRef, useState, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { aiApi } from "@/lib/api";
import { PageHeader } from "@/components/layout/PageHeader";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Bot, Send, User } from "lucide-react";
import { clsx } from "clsx";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

const SUGGESTIONS = [
  "Where is employee Amit seated?",
  "Which project is Amit assigned to?",
  "Show all available seats on Floor 3",
  "Who is sitting near Amit?",
  "How many seats are occupied for Project Indigo?",
];

export default function AssistantPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Hi! I can help you find seats, project assignments, and availability across Ethara. Try asking something like \"Where is employee Amit seated?\"",
    },
  ]);
  const [input, setInput] = useState("");
  const [email, setEmail] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const mutation = useMutation({
    mutationFn: (query: string) => aiApi.query(query, email || undefined),
    onSuccess: (data) => {
      setMessages((m) => [...m, { role: "assistant", content: data.answer }]);
    },
    onError: () => {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: "Sorry, I couldn't reach the assistant service. Please try again." },
      ]);
    },
  });

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  function send(query: string) {
    if (!query.trim()) return;
    setMessages((m) => [...m, { role: "user", content: query }]);
    setInput("");
    mutation.mutate(query);
  }

  return (
    <>
      <PageHeader
        title="AI Assistant"
        description="Ask about seats, project assignments, and availability"
      />

      <div className="flex-1 flex flex-col min-h-0 p-4 sm:p-6">
        <div className="mb-3">
          <Input
            placeholder="Optional: your email, for 'where is my seat?' style questions"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="max-w-md"
          />
        </div>

        <div
          ref={scrollRef}
          className="flex-1 min-h-0 overflow-y-auto rounded-xl border border-zinc-200 bg-white p-4 space-y-4 dark:border-zinc-800 dark:bg-zinc-950"
        >
          {messages.map((m, i) => (
            <div key={i} className={clsx("flex gap-3", m.role === "user" && "flex-row-reverse")}>
              <div
                className={clsx(
                  "flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
                  m.role === "assistant"
                    ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                    : "bg-blue-600 text-white"
                )}
              >
                {m.role === "assistant" ? <Bot size={14} /> : <User size={14} />}
              </div>
              <div
                className={clsx(
                  "max-w-[80%] rounded-xl px-3.5 py-2.5 text-sm",
                  m.role === "assistant"
                    ? "bg-zinc-100 text-zinc-800 dark:bg-zinc-900 dark:text-zinc-100"
                    : "bg-blue-600 text-white"
                )}
              >
                {m.content}
              </div>
            </div>
          ))}
          {mutation.isPending && (
            <div className="flex gap-3">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900">
                <Bot size={14} />
              </div>
              <div className="rounded-xl bg-zinc-100 px-3.5 py-2.5 text-sm text-zinc-400 dark:bg-zinc-900">
                Thinking...
              </div>
            </div>
          )}
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              className="rounded-full border border-zinc-200 px-3 py-1 text-xs text-zinc-600 hover:bg-zinc-50 dark:border-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-900"
            >
              {s}
            </button>
          ))}
        </div>

        <form
          className="mt-3 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <Input
            placeholder="Ask about a seat, project, or availability..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <Button type="submit" disabled={mutation.isPending || !input.trim()}>
            <Send size={15} />
          </Button>
        </form>
      </div>
    </>
  );
}
