"use client";

import { Suspense } from "react";

import SummarizePageContent from "./summarize-content";

const SummarizePageLoading = () => {
  return (
    <div className="main-container logged-in-container">
      <div className="content-wrapper">
        <div className="card">
          <div className="loading-container">
            <div className="loading-spinner" />
          </div>
        </div>
      </div>
    </div>
  );
};

const SummarizePage = () => {
  return (
    <Suspense fallback={<SummarizePageLoading />}>
      <SummarizePageContent />
    </Suspense>
  );
};

export default SummarizePage;
