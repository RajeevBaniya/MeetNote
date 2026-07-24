"use client";

import { Send, Loader2 } from "lucide-react";

const ChatInput = ({ value, onChange, onSubmit, disabled, sending }) => (
  <form
    onSubmit={onSubmit}
    className="p-3 border-t border-slate-800 bg-slate-900/60 flex gap-2 shrink-0 items-center"
  >
    <input
      id="chat-input"
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder="Ask a question about the meeting…"
      disabled={disabled}
      autoComplete="off"
      className="flex-1 min-w-0 bg-slate-950/50 border border-slate-800 focus:border-emerald-500/50 rounded-lg px-4 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none transition disabled:opacity-50 disabled:cursor-not-allowed"
    />
    <button
      type="submit"
      id="chat-send-button"
      disabled={!value.trim() || disabled}
      className="p-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white disabled:text-slate-600 transition shrink-0"
    >
      {sending ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        <Send className="w-4 h-4" />
      )}
    </button>
  </form>
);

export default ChatInput;
