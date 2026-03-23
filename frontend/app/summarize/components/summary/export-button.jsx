"use client";

import { useState } from "react";

import { Button } from "../ui/button";

const ExportButton = ({ summaryId, fileName, variant = "outline" }) => {
  const [isExporting, setIsExporting] = useState(false);
  const [exportType, setExportType] = useState(null);

  const handleExport = async (type) => {
    if (!summaryId) {
      alert("No summary available to export");
      return;
    }

    setIsExporting(true);
    setExportType(type);

    try {
      const baseUrl =
        process.env.NEXT_PUBLIC_SUMMARY_API_URL || "http://localhost:5000";
      const response = await fetch(
        `${baseUrl}/api/export/${type}/${summaryId}`,
        {
          method: "GET",
        },
      );

      if (!response.ok) {
        const errorText = await response.text();
        let errorData;
        try {
          errorData = JSON.parse(errorText);
        } catch {
          errorData = {
            error: errorText || `Server returned status ${response.status}`,
          };
        }
        throw new Error(
          errorData.error ||
            errorData.details ||
            `Server returned status ${response.status}`,
        );
      }

      const contentType = response.headers.get("content-type") || "";

      if (type === "pdf") {
        if (!contentType.includes("application/pdf")) {
          const text = await response.text();
          let errorData;
          try {
            errorData = JSON.parse(text);
          } catch {
            errorData = { error: "Failed to generate PDF" };
          }
          throw new Error(
            errorData.error || errorData.details || "Failed to generate PDF",
          );
        }
      }

      const blob = await response.blob();

      if (blob.size === 0) {
        throw new Error("Received empty file from server");
      }

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.style.display = "none";

      const contentDisposition = response.headers.get("content-disposition");
      const fileExtension = type === "pdf" ? "pdf" : "docx";
      let downloadFileName =
        fileName || `meeting-notes-${summaryId}.${fileExtension}`;

      if (contentDisposition) {
        const fileNameMatch = contentDisposition.match(
          /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/,
        );
        if (fileNameMatch && fileNameMatch[1]) {
          downloadFileName = decodeURIComponent(
            fileNameMatch[1].replace(/['"]/g, ""),
          );
        }
      } else {
        if (!downloadFileName.endsWith(`.${fileExtension}`)) {
          downloadFileName =
            downloadFileName.replace(/\.[^.]+$/, "") + `.${fileExtension}`;
        }
      }

      link.download = downloadFileName;
      document.body.appendChild(link);
      link.click();

      setTimeout(() => {
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }, 100);
    } catch (error) {
      let message = error.message || "Unknown error occurred";
      alert(`Failed to export ${type.toUpperCase()}: ${message}`);
    } finally {
      setIsExporting(false);
      setExportType(null);
    }
  };

  return (
    <div className="flex gap-2">
      <Button
        variant={variant}
        size="sm"
        onClick={() => handleExport("pdf")}
        disabled={isExporting || !summaryId}
        className="flex items-center gap-2"
      >
        {isExporting && exportType === "pdf" ? (
          <>
            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-current" />
            <span>Exporting...</span>
          </>
        ) : (
          <>
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
                d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
              />
            </svg>
            <span>PDF</span>
          </>
        )}
      </Button>

      <Button
        variant={variant}
        size="sm"
        onClick={() => handleExport("word")}
        disabled={isExporting || !summaryId}
        className="flex items-center gap-2"
      >
        {isExporting && exportType === "word" ? (
          <>
            <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-current" />
            <span>Exporting...</span>
          </>
        ) : (
          <>
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
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <span>Word</span>
          </>
        )}
      </Button>
    </div>
  );
};

export default ExportButton;
