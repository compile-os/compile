"use client";

import { useState, useRef } from "react";
import { Upload, Check, Loader2, X } from "lucide-react";

interface ApplicationFormProps {
  roleTitle?: string;
}

export default function ApplicationForm({ roleTitle }: ApplicationFormProps) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [linkedin, setLinkedin] = useState("");
  const [resume, setResume] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.type !== "application/pdf") {
        setError("Please upload a PDF file");
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        setError("File size must be less than 5MB");
        return;
      }
      setError("");
      setResume(file);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!fullName || !email || !linkedin || !resume) {
      setError("Please fill in all required fields");
      return;
    }

    setIsSubmitting(true);

    // Simulate submission - replace with actual API call
    await new Promise((resolve) => setTimeout(resolve, 1500));

    setIsSubmitting(false);
    setIsSubmitted(true);
  };

  if (isSubmitted) {
    return (
      <div className="p-8 rounded-xl border border-green-500/30 bg-green-500/10 text-center">
        <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-4">
          <Check className="w-6 h-6 text-green-400" />
        </div>
        <h3 className="text-xl font-medium text-green-400 mb-2">Application Submitted</h3>
        <p className="text-gray-400">
          Thank you for your interest in Compile. We will review your application and get back to you soon.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <h3 className="text-lg font-medium mb-6">
        {roleTitle ? `Apply for ${roleTitle}` : "Apply for this Position"}
      </h3>

      <div>
        <label className="block text-sm text-gray-400 mb-2">
          Full Name <span className="text-red-400">*</span>
        </label>
        <input
          type="text"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder="Enter your full name"
          className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500/50 transition"
          required
        />
      </div>

      <div>
        <label className="block text-sm text-gray-400 mb-2">
          Email Address <span className="text-red-400">*</span>
        </label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Enter your email address"
          className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500/50 transition"
          required
        />
      </div>

      <div>
        <label className="block text-sm text-gray-400 mb-2">
          LinkedIn Profile <span className="text-red-400">*</span>
        </label>
        <input
          type="url"
          value={linkedin}
          onChange={(e) => setLinkedin(e.target.value)}
          placeholder="https://linkedin.com/in/yourprofile"
          className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500/50 transition"
          required
        />
      </div>

      <div>
        <label className="block text-sm text-gray-400 mb-2">
          Resume <span className="text-red-400">*</span>
        </label>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          className="hidden"
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="w-full px-4 py-3 rounded-lg bg-white/5 border border-white/10 text-left flex items-center justify-between hover:border-white/20 transition"
        >
          <span className={resume ? "text-white" : "text-gray-500"}>
            {resume ? resume.name : "No file chosen"}
          </span>
          {resume ? (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setResume(null);
                if (fileInputRef.current) fileInputRef.current.value = "";
              }}
              className="text-gray-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          ) : (
            <Upload className="w-4 h-4 text-gray-400" />
          )}
        </button>
        <p className="text-xs text-gray-500 mt-2">PDF files only, max 5MB</p>
      </div>

      {error && (
        <p className="text-red-400 text-sm">{error}</p>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full py-3 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:bg-purple-600/50 disabled:cursor-not-allowed text-white font-medium transition flex items-center justify-center gap-2"
      >
        {isSubmitting ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Submitting...
          </>
        ) : (
          "Submit Application"
        )}
      </button>
    </form>
  );
}
