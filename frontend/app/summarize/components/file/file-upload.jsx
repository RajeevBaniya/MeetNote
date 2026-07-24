"use client";

import { useState, useEffect, useCallback } from "react";

import { apiFetch } from "../../lib/api";
import { Button } from "../ui/button";

const PREVIEW_COLLAPSED_CHARS = 400;

const FILE_TYPE_LABELS = Object.freeze({
  txt: "Text File",
  pdf: "PDF Document",
  docx: "Word Document",
});

const MIME_MAP = Object.freeze({
  ".txt": "text/plain",
  ".pdf": "application/pdf",
  ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
});

const getFileExtension = (filename) => {
  const lastDot = filename.lastIndexOf(".");
  return lastDot !== -1 ? filename.slice(lastDot).toLowerCase() : "";
};

const formatFileSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const TranscriptPreview = ({ transcript, label }) => {
  const [expanded, setExpanded] = useState(false);

  const isLong = transcript.length > PREVIEW_COLLAPSED_CHARS;
  const displayedText =
    expanded || !isLong
      ? transcript
      : transcript.substring(0, PREVIEW_COLLAPSED_CHARS);

  const handleToggle = useCallback(() => {
    setExpanded((prev) => !prev);
  }, []);

  return (
    <div className="transcript-preview">
      <div className="flex items-center justify-between mb-1">
        <p className="text-sm text-slate-400">{label}</p>
        <span className="text-xs text-slate-500">
          {transcript.length.toLocaleString()} characters extracted
        </span>
      </div>
      <p className="text-sm text-slate-300 whitespace-pre-wrap">
        {displayedText}
        {!expanded && isLong ? "…" : ""}
      </p>
      {isLong && (
        <button
          onClick={handleToggle}
          className="mt-2 text-xs text-emerald-400 hover:text-emerald-300 transition-colors"
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
    </div>
  );
};

const FileUpload = ({ onFileUpload, transcript }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);

  const [maxFileSize, setMaxFileSize] = useState(10 * 1024 * 1024);
  const [supportedExtensions, setSupportedExtensions] = useState([
    ".txt",
    ".pdf",
    ".docx",
  ]);

  useEffect(() => {
    let active = true;
    const fetchConfig = async () => {
      try {
        const response = await apiFetch("/api/upload/config");
        if (active && response) {
          if (typeof response.maxFileSize === "number") {
            setMaxFileSize(response.maxFileSize);
          }
          if (Array.isArray(response.supportedExtensions)) {
            setSupportedExtensions(response.supportedExtensions);
          }
        }
      } catch (err) {
        console.error("Failed to fetch upload config:", err);
      }
    };
    fetchConfig();
    return () => {
      active = false;
    };
  }, []);

  const maxFileSizeMB = Math.floor(maxFileSize / (1024 * 1024));

  const isValidFileType = (file) => {
    const ext = getFileExtension(file.name);
    if (supportedExtensions.includes(ext)) {
      return true;
    }
    const mimeType = MIME_MAP[ext];
    return mimeType && file.type === mimeType;
  };

  const isValidFileSize = (file) => file.size <= maxFileSize;

  const validateFile = (file) => {
    if (!file) {
      return { valid: false, error: "No file selected" };
    }
    if (!isValidFileType(file)) {
      return {
        valid: false,
        error: `Invalid file type. Allowed: ${supportedExtensions.join(", ")}`,
      };
    }
    if (!isValidFileSize(file)) {
      return {
        valid: false,
        error: `File too large. Maximum size: ${maxFileSizeMB}MB`,
      };
    }
    return { valid: true, error: null };
  };

  const handleFileUpload = async (file) => {
    const validation = validateFile(file);
    if (!validation.valid) {
      alert(validation.error);
      return;
    }

    setIsUploading(true);

    const formData = new FormData();
    formData.append("transcript", file);

    try {
      const response = await apiFetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      const fileInfo = {
        name: file.name,
        type: response.fileType,
        size: file.size,
      };

      setUploadedFile(fileInfo);
      onFileUpload(response.content);
    } catch (error) {
      const message = error.message || "Unknown error";
      alert(`Error uploading file: ${message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    handleFileUpload(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDragEnter = () => {
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleFileInput = (e) => {
    const file = e.target.files[0];
    if (file) {
      handleFileUpload(file);
    }
  };

  const dropzoneClass = isDragging
    ? "border-emerald-400 bg-emerald-500/10"
    : "border-slate-600 bg-slate-800/30";

  return (
    <div className="card">
      <h2 className="section-title mb-4">Upload Meeting Transcript</h2>

      <div
        className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors ${dropzoneClass}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
      >
        {isUploading ? (
          <div className="text-emerald-400">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-400 mx-auto mb-2" />
            Processing file...
          </div>
        ) : (
          <>
            <div className="mb-4">
              <svg
                className="mx-auto h-12 w-12 text-emerald-400"
                stroke="currentColor"
                fill="none"
                viewBox="0 0 48 48"
              >
                <path
                  d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <p className="text-lg mb-2 text-slate-300">
              Drop your file here, or
            </p>
            <div>
              <input
                type="file"
                accept=".txt,.pdf,.docx,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={handleFileInput}
                className="hidden"
                id="file-input"
              />
              <Button asChild>
                <label htmlFor="file-input" className="cursor-pointer">
                  Browse Files
                </label>
              </Button>
            </div>
            <p className="text-sm text-slate-500 mt-2">
              Supported: {supportedExtensions.join(", ")} (up to {maxFileSizeMB}
              MB)
            </p>
          </>
        )}
      </div>

      {transcript && uploadedFile && (
        <TranscriptPreview
          transcript={transcript}
          label={`${FILE_TYPE_LABELS[uploadedFile.type] || "File"} · ${uploadedFile.name} · ${formatFileSize(uploadedFile.size)}`}
        />
      )}

      {transcript && !uploadedFile && (
        <TranscriptPreview transcript={transcript} label="Transcript preview" />
      )}
    </div>
  );
};

export default FileUpload;
