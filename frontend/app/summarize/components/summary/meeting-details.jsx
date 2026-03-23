"use client";

import { useRef, useState } from "react";

import { SlCalender } from "react-icons/sl";

import { Button } from "../ui/button";
import TagsEditor from "./tags-editor";

const MEETING_TYPES = [
  { value: "", label: "Select type..." },
  { value: "team", label: "Team Meeting" },
  { value: "one-on-one", label: "1-on-1" },
  { value: "client", label: "Client Meeting" },
  { value: "standup", label: "Standup" },
  { value: "project-review", label: "Project Review" },
  { value: "brainstorm", label: "Brainstorming" },
  { value: "interview", label: "Interview" },
  { value: "training", label: "Training" },
  { value: "other", label: "Other" },
];

const MeetingDetails = ({ meetingData, onUpdate }) => {
  const [participantInput, setParticipantInput] = useState("");
  const dateTimeInputRef = useRef(null);

  const handleChange = (field, value) => {
    onUpdate({ ...meetingData, [field]: value });
  };

  const addParticipant = () => {
    const trimmed = participantInput.trim();
    if (!trimmed) return;
    if (meetingData.participants.includes(trimmed)) return;

    onUpdate({
      ...meetingData,
      participants: [...meetingData.participants, trimmed],
    });
    setParticipantInput("");
  };

  const removeParticipant = (name) => {
    onUpdate({
      ...meetingData,
      participants: meetingData.participants.filter((p) => p !== name),
    });
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addParticipant();
    }
  };

  const inputClass =
    "w-full p-3 bg-slate-800/50 border border-slate-600 rounded-lg text-slate-200 placeholder-slate-500 focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-colors";

  return (
    <div className="card">
      <h2 className="section-title mb-4">Meeting Details</h2>

      <div className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Meeting Title
            </label>
            <input
              type="text"
              value={meetingData.meetingTitle}
              onChange={(e) => handleChange("meetingTitle", e.target.value)}
              placeholder="e.g., Weekly Team Sync"
              className={inputClass}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Meeting Type
            </label>
            <select
              value={meetingData.meetingType}
              onChange={(e) => handleChange("meetingType", e.target.value)}
              className={inputClass}
            >
              {MEETING_TYPES.map((type) => (
                <option
                  key={type.value}
                  value={type.value}
                  className="bg-slate-800"
                >
                  {type.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Meeting Date & Time
            </label>
            <div className="relative">
              <input
                ref={dateTimeInputRef}
                type="datetime-local"
                value={meetingData.meetingDate}
                onChange={(e) => handleChange("meetingDate", e.target.value)}
                className={`date-input-custom-icon ${inputClass} pr-10`}
              />
              <button
                type="button"
                onClick={() => {
                  if (dateTimeInputRef.current) {
                    dateTimeInputRef.current.showPicker?.();
                    dateTimeInputRef.current.focus();
                  }
                }}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-300 hover:text-white transition-colors cursor-pointer z-10"
                aria-label="Open calendar"
              >
                <SlCalender className="w-5 h-5" />
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Location / Meeting Link
            </label>
            <input
              type="text"
              value={meetingData.location}
              onChange={(e) => handleChange("location", e.target.value)}
              placeholder="e.g., Conference Room A or Zoom link"
              className={inputClass}
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            Participants
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={participantInput}
              onChange={(e) => setParticipantInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Add participant name"
              className={`flex-1 ${inputClass}`}
            />
            <Button
              type="button"
              variant="outline"
              onClick={addParticipant}
              disabled={!participantInput.trim()}
            >
              Add
            </Button>
          </div>

          {meetingData.participants.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {meetingData.participants.map((name, index) => (
                <span
                  key={index}
                  className="inline-flex items-center gap-1 px-3 py-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full text-sm"
                >
                  {name}
                  <button
                    type="button"
                    onClick={() => removeParticipant(name)}
                    className="ml-1 text-emerald-400 hover:text-emerald-200 focus:outline-none"
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1">
            Tags
          </label>
          <TagsEditor
            tags={meetingData.tags || []}
            onChange={(newTags) => handleChange("tags", newTags)}
            placeholder="Type a tag and press Enter..."
          />
          <p className="text-xs text-slate-500 mt-1">
            Press Enter or comma to add a tag
          </p>
        </div>
      </div>
    </div>
  );
};

export default MeetingDetails;
