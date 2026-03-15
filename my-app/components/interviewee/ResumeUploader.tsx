"use client";

import { useEffect, useMemo, useState } from "react";

type StoredResumeMeta = {
  resumeId: string;
  name: string;
  size: number;
  type: string;
  lastModified: number;
  storedAt: string;
  extractedKeys?: string[];
  contactName?: string;
};

export const RESUME_STORAGE_KEY = "umamaj.resumeMeta";
export const RESUME_ID_KEY = "umamaj.resumeId";

function formatBytes(bytes: number) {
  const units = ["B", "KB", "MB", "GB"];
  let v = bytes;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${v.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

export function ResumeUploader() {
  const [stored, setStored] = useState<StoredResumeMeta | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const BACKEND_URL =
    process.env.NEXT_PUBLIC_BACKEND_URL?.trim() || "http://localhost:8000";

  useEffect(() => {
    const raw = localStorage.getItem(RESUME_STORAGE_KEY);
    if (!raw) return;
    try {
      setStored(JSON.parse(raw) as StoredResumeMeta);
    } catch {
      localStorage.removeItem(RESUME_STORAGE_KEY);
    }
  }, []);

  const accept = useMemo(() => {
    // PDF + common Word formats
    return [
      "application/pdf",
      "application/msword",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "text/plain",
      "text/markdown",
    ].join(",");
  }, []);

  async function onPickFile(file: File | null) {
    setError(null);
    if (!file) return;

    const isAllowedByMime = accept.split(",").includes(file.type);
    const ext = file.name.split(".").pop()?.toLowerCase();
    const isAllowedByExt = ext ? ["pdf", "doc", "docx", "txt", "md"].includes(ext) : false;
    if (!isAllowedByMime && !isAllowedByExt) {
      setError("Please upload a PDF, Word document, or TXT file.");
      return;
    }

    setIsUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${BACKEND_URL}/api/resume/upload`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        const detail =
          body && typeof body === "object" && "detail" in body
            ? String((body as any).detail)
            : `Upload failed (${res.status})`;
        throw new Error(detail);
      }

      const data = (await res.json()) as {
        resume_id: string;
        extracted_keys?: string[];
        contact_name?: string;
      };

      const meta: StoredResumeMeta = {
        resumeId: data.resume_id,
        name: file.name,
        size: file.size,
        type: file.type,
        lastModified: file.lastModified,
        storedAt: new Date().toISOString(),
        extractedKeys: data.extracted_keys ?? [],
        contactName: data.contact_name ?? "",
      };

      localStorage.setItem(RESUME_ID_KEY, data.resume_id);
      localStorage.setItem(RESUME_STORAGE_KEY, JSON.stringify(meta));
      setStored(meta);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface-elevated)] overflow-hidden">
      <div className="border-b border-[var(--color-border)] px-5 py-3">
        <h2 className="text-base font-semibold text-[var(--color-primary)]">
          Upload your resume
        </h2>
        <p className="mt-1 text-sm text-[var(--color-muted)]">
          We upload your resume to the backend and store the parsed JSON for future use.
        </p>
      </div>

      <div className="p-5">
        <label className="block">
          <span className="text-sm font-medium text-[var(--color-muted)]">
            Resume file (PDF/DOC/DOCX)
          </span>
          <input
            type="file"
            accept={accept}
            className="mt-2 block w-full text-sm"
            onChange={(e) => void onPickFile(e.target.files?.item(0) ?? null)}
            disabled={isUploading}
          />
        </label>

        {isUploading && (
          <p className="mt-3 text-sm text-[var(--color-muted)]">
            Uploading and parsing…
          </p>
        )}
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

        {stored && (
          <div className="mt-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{stored.name}</p>
                {stored.contactName && (
                  <p className="mt-0.5 text-xs text-[var(--color-muted)]">
                    Detected name: {stored.contactName}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => {
                  localStorage.removeItem(RESUME_STORAGE_KEY);
                  localStorage.removeItem(RESUME_ID_KEY);
                  setStored(null);
                }}
                className="rounded-lg border border-[var(--color-border)] px-3 py-1.5 text-sm hover:bg-black/5"
              >
                Remove
              </button>
            </div>
            <p className="mt-1 text-xs text-[var(--color-muted)]">
              {formatBytes(stored.size)} · {stored.type || "unknown type"}
            </p>
            <p className="mt-1 text-xs text-[var(--color-muted)]">
              Saved: {new Date(stored.storedAt).toLocaleString()}
            </p>
            {stored.extractedKeys && stored.extractedKeys.length > 0 && (
              <p className="mt-2 text-xs text-[var(--color-muted)]">
                Extracted: {stored.extractedKeys.join(", ")}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

