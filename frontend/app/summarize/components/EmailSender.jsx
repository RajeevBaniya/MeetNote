"use client";

import { useState } from "react";
import { apiFetch } from "../lib/api";
import { Button } from "./ui/button";

const EmailSender = ({ summary }) => {
  const [recipients, setRecipients] = useState([""]);
  const [subject, setSubject] = useState("Meeting Summary");
  const [isSending, setIsSending] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  const addRecipient = () => {
    setRecipients([...recipients, ""]);
  };

  const removeRecipient = (index) => {
    const newRecipients = recipients.filter((_, i) => i !== index);
    setRecipients(newRecipients.length > 0 ? newRecipients : [""]);
  };

  const updateRecipient = (index, value) => {
    setRecipients(recipients.map((r, i) => (i === index ? value : r)));
  };

  const sendEmail = async () => {
    const validRecipients = recipients.filter((email) => email.trim());

    if (validRecipients.length === 0) {
      setError("Please add at least one email address");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const invalidEmails = validRecipients.filter(
      (email) => !emailRegex.test(email),
    );

    if (invalidEmails.length > 0) {
      setError(`Invalid email addresses: ${invalidEmails.join(", ")}`);
      return;
    }

    setIsSending(true);
    setError("");
    setSuccess("");

    try {
      await apiFetch("/api/email/send", {
        method: "POST",
        body: JSON.stringify({
          recipients: validRecipients,
          summary: summary,
          subject: subject,
        }),
      });
      setSuccess(
        `Summary sent successfully to ${validRecipients.length} recipient(s)`,
      );
    } catch (err) {
      setError("Failed to send email: " + (err.message || "Unknown error"));
    } finally {
      setIsSending(false);
    }
  };

  const inputClass =
    "w-full p-3 bg-slate-800/50 border border-slate-600 rounded-lg text-slate-200 placeholder-slate-500 focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-colors";

  return (
    <div className="card">
      <h2 className="section-title mb-4">Share Summary via Email</h2>

      <div className="space-y-4 flex flex-col items-center">
        <div className="w-full">
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Subject
          </label>
          <input
            type="text"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className={inputClass}
            placeholder="Meeting Summary"
          />
        </div>

        <div className="w-full">
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Recipients
          </label>
          {recipients.map((recipient, index) => (
            <div key={index} className="flex gap-2 mb-2">
              <input
                type="email"
                value={recipient}
                onChange={(e) => updateRecipient(index, e.target.value)}
                placeholder="Enter email address"
                className={`flex-1 ${inputClass}`}
              />
              {recipients.length > 1 && (
                <Button
                  variant="outline"
                  size="sm"
                  className="text-red-400 hover:text-red-300 border-red-500/30 hover:bg-red-500/10"
                  onClick={() => removeRecipient(index)}
                >
                  Remove
                </Button>
              )}
            </div>
          ))}
          <Button
            variant="ghost"
            size="sm"
            onClick={addRecipient}
            className="text-slate-400 hover:text-slate-200"
          >
            + Add another recipient
          </Button>
        </div>

        {error && (
          <div className="w-full p-3 bg-red-500/15 border border-red-500/30 rounded-lg">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        {success && (
          <div className="w-full p-3 bg-emerald-500/15 border border-emerald-500/30 rounded-lg">
            <p className="text-emerald-400 text-sm">{success}</p>
          </div>
        )}

        <Button
          onClick={sendEmail}
          disabled={isSending}
          className="w-auto px-12"
          size="default"
        >
          {isSending ? (
            <div className="flex items-center justify-center">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
              Sending Email...
            </div>
          ) : (
            "Send Summary"
          )}
        </Button>
      </div>
    </div>
  );
};

export default EmailSender;
