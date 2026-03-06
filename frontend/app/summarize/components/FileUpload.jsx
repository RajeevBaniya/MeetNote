"use client";

import { useState } from "react";
import { apiFetch } from "../lib/api";
import { Button } from "./ui/button";

const ALLOWED_EXTENSIONS = Object.freeze([".txt", ".pdf", ".docx"]);
const ALLOWED_MIME_TYPES = Object.freeze([
  "text/plain",
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]);
const MAX_FILE_SIZE_MB = 10;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

const FILE_TYPE_LABELS = Object.freeze({
  txt: "Text File",
  pdf: "PDF Document",
  docx: "Word Document",
});

function getFileExtension(filename) {
  const lastDot = filename.lastIndexOf(".");
  return lastDot !== -1 ? filename.slice(lastDot).toLowerCase() : "";
}

function isValidFileType(file) {
  const ext = getFileExtension(file.name);
  return (
    ALLOWED_EXTENSIONS.includes(ext) || ALLOWED_MIME_TYPES.includes(file.type)
  );
}

function isValidFileSize(file) {
  return file.size <= MAX_FILE_SIZE_BYTES;
}

function validateFile(file) {
  if (!file) {
    return { valid: false, error: "No file selected" };
  }

  if (!isValidFileType(file)) {
    return {
      valid: false,
      error: `Invalid file type. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`,
    };
  }

  if (!isValidFileSize(file)) {
    return {
      valid: false,
      error: `File too large. Maximum size: ${MAX_FILE_SIZE_MB}MB`,
    };
  }

  return { valid: true, error: null };
}

function FileUpload({ onFileUpload, transcript }) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);

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

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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
              Supported: .txt, .pdf, .docx (up to {MAX_FILE_SIZE_MB}MB)
            </p>
          </>
        )}
      </div>

      {transcript && uploadedFile && (
        <div className="transcript-preview">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-medium text-emerald-400">
              {FILE_TYPE_LABELS[uploadedFile.type] || "File"}
            </span>
            <span className="text-sm text-slate-500">•</span>
            <span className="text-sm text-slate-400">{uploadedFile.name}</span>
            <span className="text-sm text-slate-500">•</span>
            <span className="text-sm text-slate-500">
              {formatFileSize(uploadedFile.size)}
            </span>
          </div>
          <p className="text-sm text-slate-400 mb-1">Extracted text preview:</p>
          <p className="text-sm text-slate-300">
            {transcript.substring(0, 300)}
            {transcript.length > 300 ? "..." : ""}
          </p>
        </div>
      )}

      {transcript && !uploadedFile && (
        <div className="transcript-preview">
          <p className="text-sm text-slate-400 mb-2">Transcript preview:</p>
          <p className="text-sm text-slate-300">
            {transcript.substring(0, 300)}
            {transcript.length > 300 ? "..." : ""}
          </p>
        </div>
      )}
    </div>
  );
}

export default FileUpload;
