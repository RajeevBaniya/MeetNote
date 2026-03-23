"use client";

import { useState } from "react";

import { Button } from "../ui/button";
import ExportButton from "./export-button";

const renderMarkdown = (text) => {
  if (!text) return "";

  const lines = text.split("\n");
  const result = [];
  let inList = false;
  let inSubList = false;

  lines.forEach((line) => {
    const trimmed = line.trim();

    if (!trimmed) {
      if (inList || inSubList) {
        result.push("</ul>");
        inList = false;
        inSubList = false;
      }
      result.push("<br />");
      return;
    }

    if (
      (trimmed.startsWith("**") &&
        trimmed.endsWith("**") &&
        !trimmed.includes("*")) ||
      trimmed.match(/^\*\*[^*]+\*\*$/)
    ) {
      if (inList || inSubList) {
        result.push("</ul>");
        inList = false;
        inSubList = false;
      }
      const heading = trimmed.replace(/\*\*/g, "");
      result.push(
        `<h3 class="font-semibold text-slate-100 mt-4 mb-2 text-base">${heading}</h3>`
      );
      return;
    }

    if (trimmed.startsWith("* ") && !trimmed.startsWith("**")) {
      if (!inList) {
        result.push('<ul class="list-disc list-inside mb-3 ml-4 space-y-1">');
        inList = true;
      }
      if (inSubList) {
        result.push("</ul>");
        inSubList = false;
      }
      const content = trimmed.substring(2).trim();
      const processed = content.replace(
        /\*\*(.+?)\*\*/g,
        '<strong class="text-slate-200">$1</strong>'
      );
      result.push(`<li class="mb-1">${processed}</li>`);
      return;
    }

    if (trimmed.startsWith("+ ")) {
      if (!inList) {
        result.push('<ul class="list-disc list-inside mb-3 ml-4 space-y-1">');
        inList = true;
      }
      if (!inSubList) {
        result.push('<ul class="list-disc list-inside mb-2 ml-6 space-y-1">');
        inSubList = true;
      }
      const content = trimmed.substring(2).trim();
      const processed = content.replace(
        /\*\*(.+?)\*\*/g,
        '<strong class="text-slate-200">$1</strong>'
      );
      result.push(`<li class="mb-1">${processed}</li>`);
      return;
    }

    if (inList || inSubList) {
      result.push("</ul>");
      if (inSubList) {
        result.push("</ul>");
        inSubList = false;
      }
      inList = false;
    }

    const processed = trimmed
      .replace(/\*\*(.+?)\*\*/g, '<strong class="text-slate-200">$1</strong>')
      .replace(/\*(.+?)\*/g, "<em>$1</em>");
    result.push(`<p class="mb-2">${processed}</p>`);
  });

  if (inList || inSubList) {
    result.push("</ul>");
    if (inSubList) {
      result.push("</ul>");
    }
  }

  return result.join("");
};

const SummaryEditor = ({ summary, setSummary, summaryId, meetingTitle }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedSummary, setEditedSummary] = useState(summary);

  const handleSave = () => {
    setSummary(editedSummary);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditedSummary(summary);
    setIsEditing(false);
  };

  const handleEdit = () => {
    setEditedSummary(summary);
    setIsEditing(true);
  };

  return (
    <div className="card">
      <div className="flex justify-between items-center mb-4">
        <h2 className="section-title">Generated Summary</h2>
        {!isEditing && (
          <div className="flex items-center gap-3">
            {summaryId && (
              <ExportButton
                summaryId={summaryId}
                fileName={meetingTitle ? `${meetingTitle}.pdf` : undefined}
              />
            )}
            <Button variant="outline" onClick={handleEdit} className="px-6">
              Edit
            </Button>
          </div>
        )}
      </div>

      {isEditing ? (
        <div className="flex flex-col flex-1 gap-4">
          <textarea
            value={editedSummary}
            onChange={(e) => setEditedSummary(e.target.value)}
            className="flex-1 w-full p-4 bg-slate-800/50 border border-slate-600 rounded-lg text-slate-200 focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 resize-none min-h-[16rem] max-h-[400px]"
            placeholder="Edit your summary here..."
          />
          <div className="button-container gap-2">
            <Button onClick={handleSave} className="w-auto px-6">
              Save Changes
            </Button>
            <Button
              variant="secondary"
              onClick={handleCancel}
              className="w-auto px-6"
            >
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-hidden">
          <div className="min-h-[16rem] max-h-[400px] p-4 bg-slate-800/40 rounded-lg border border-slate-700/50 overflow-y-auto">
            <div
              className="text-sm text-slate-300 font-sans prose prose-sm prose-invert max-w-none"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(summary) }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default SummaryEditor;
