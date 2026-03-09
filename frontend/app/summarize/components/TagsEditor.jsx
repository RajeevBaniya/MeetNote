"use client";

import { useState, useCallback } from "react";

const TagsEditor = ({ tags = [], onChange, placeholder = "Add tags..." }) => {
  const [inputValue, setInputValue] = useState("");

  const handleInputChange = useCallback((e) => {
    setInputValue(e.target.value);
  }, []);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter" || e.key === ",") {
        e.preventDefault();
        const newTag = inputValue.trim().toLowerCase();
        if (newTag && !tags.includes(newTag)) {
          onChange([...tags, newTag]);
        }
        setInputValue("");
      }
      if (e.key === "Backspace" && inputValue === "" && tags.length > 0) {
        onChange(tags.slice(0, -1));
      }
    },
    [inputValue, tags, onChange]
  );

  const handleRemoveTag = useCallback(
    (tagToRemove) => {
      onChange(tags.filter((tag) => tag !== tagToRemove));
    },
    [tags, onChange]
  );

  const handleBlur = useCallback(() => {
    const newTag = inputValue.trim().toLowerCase();
    if (newTag && !tags.includes(newTag)) {
      onChange([...tags, newTag]);
    }
    setInputValue("");
  }, [inputValue, tags, onChange]);

  return (
    <div className="flex flex-wrap items-center gap-2 p-2 bg-slate-800 border border-slate-700 rounded-lg min-h-[42px]">
      {tags.map((tag) => (
        <span
          key={tag}
          className="inline-flex items-center gap-1 px-2 py-1 bg-slate-700 text-slate-200 rounded text-sm"
        >
          #{tag}
          <button
            type="button"
            onClick={() => handleRemoveTag(tag)}
            className="ml-1 text-slate-400 hover:text-slate-200"
          >
            <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
      <input
        type="text"
        value={inputValue}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        placeholder={tags.length === 0 ? placeholder : ""}
        className="flex-1 min-w-[100px] bg-transparent border-none outline-none text-slate-100 text-sm placeholder-slate-500"
      />
    </div>
  );
};

export default TagsEditor;
