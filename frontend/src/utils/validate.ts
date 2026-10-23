export const MAX_RESUME_MB = 5;

/** Client-side pre-check for a nicer error. The server re-validates by file content. */
export function validateResumeFile(file: { name: string; size: number }): string | null {
  const ext = file.name.toLowerCase().split(".").pop();
  if (ext !== "pdf" && ext !== "docx") return "Please choose a PDF or DOCX file.";
  if (file.size === 0) return "That file is empty.";
  if (file.size > MAX_RESUME_MB * 1024 * 1024) return `The file is larger than ${MAX_RESUME_MB} MB.`;
  return null;
}
