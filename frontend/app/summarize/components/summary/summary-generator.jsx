"use client";

import { useState } from "react";

import { apiFetch } from "../../lib/api";
import { Button } from "../ui/button";

const PRESET_INSTRUCTIONS = [
  "Summarize in bullet points for executives",
  "Highlight only action items and next steps",
  "Create a brief overview with key decisions",
  "List all participants and their main contributions",
  "Extract important dates, deadlines and deliverables",
];

const SummaryGenerator = ({
  transcript,
  setSummary,
  setStructured,
  isLoading,
  setIsLoading,
  meetingData,
  setSummaryId,
  meetingId,
  onLiveGenerate = null,
  isGeneratingRef = null,
}) => {
  const [instruction, setInstruction] = useState("");
  const [error, setError] = useState("");

  const generateSummary = async () => {
    if (!transcript.trim()) {
      setError("Please upload a transcript first");
      return;
    }

    if (!instruction.trim()) {
      setError("Please provide an instruction");
      return;
    }

    if (typeof onLiveGenerate === "function") {
      setIsLoading(true);
      setError("");
      try {
        await new Promise((resolve) => setTimeout(resolve, 350));
        await onLiveGenerate(instruction.trim());
      } catch (err) {
        const message = err?.message || "Generation failed";
        setError(message);
      } finally {
        setIsLoading(false);
      }
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const response = await apiFetch("/api/summary/generate", {
        method: "POST",
        body: JSON.stringify({
          transcript,
          instruction,
          title: new Date().toLocaleString(),
          meetingId: meetingId || null,
          meetingTitle: meetingData.meetingTitle || null,
          meetingDate: meetingData.meetingDate || null,
          meetingType: meetingData.meetingType || null,
          participants: meetingData.participants || [],
          location: meetingData.location || null,
          tags: meetingData.tags || [],
          extractStructured: true,
        }),
      });

      setSummary(response.summary);

      if (response.structured) {
        setStructured(response.structured);
      }

      if (response.savedId && setSummaryId) {
        setSummaryId(response.savedId);
      }
    } catch (err) {
      const message = err.message || "Unknown error";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const selectPreset = (preset) => {
    setInstruction(preset);
  };

  return (
    <div className="card">
      <h2 className="section-title mb-4">Generate Summary</h2>

      <div className="space-y-4 flex flex-col items-center">
        <div className="w-full">
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Custom Instruction
          </label>
          <textarea
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            placeholder="e.g., Summarize in bullet points for executives"
            className="w-full p-3 bg-slate-800/50 border border-slate-600 rounded-lg text-slate-200 placeholder-slate-500 focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-colors"
            rows="3"
          />
        </div>

        <div className="w-full">
          <p className="text-sm font-medium text-slate-300 mb-2">
            Quick options:
          </p>
          <div className="flex flex-wrap gap-2 justify-center">
            {PRESET_INSTRUCTIONS.map((preset, index) => (
              <Button
                key={index}
                variant="outline"
                size="sm"
                onClick={() => selectPreset(preset)}
              >
                {preset}
              </Button>
            ))}
          </div>
        </div>

        {error && (
          <div className="p-3 bg-red-500/15 border border-red-500/30 rounded-lg w-full">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        <Button
          onClick={generateSummary}
          disabled={
            isLoading ||
            !transcript.trim() ||
            !instruction.trim() ||
            Boolean(isGeneratingRef?.current)
          }
          className="w-auto px-12"
          size="default"
        >
          {isLoading ? (
            <div className="flex items-center justify-center">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2" />
              Generating Summary...
            </div>
          ) : (
            "Generate Summary"
          )}
        </Button>
      </div>
    </div>
  );
};

export default SummaryGenerator;
