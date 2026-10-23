export type Role = "USER" | "ADMIN" | "SUPER_ADMIN";
export interface User { id: string; email: string; full_name: string; role: Role; email_verified_at: string | null; created_at: string }
export interface Page<T> { items: T[]; total: number; page: number; page_size: number }
export type Level = "required" | "preferred" | "uncertain";
export type Status = "demonstrated" | "listed" | "not_found";
export interface Evidence { section: string; snippet: string }
export interface ComparisonItem {
  skill: string; category: string; level: Level; confidence: string; reason: string; evidence: Evidence[] | string;
  status: Status; weight: number; credit: number; points: number;
}
export interface Comparison {
  score: number | null;
  score_explanation: { formula: string; weights: Record<string, number>; credits: Record<string, number>; total_weight: number; earned_points: number; disclaimer: string };
  coverage: Record<Level, { total: number; demonstrated: number; listed: number; not_found: number; percent: number | null }>;
  items: ComparisonItem[];
  matched: ComparisonItem[];
  not_found: ComparisonItem[];
  manual_confirmation: { kind: string; skill: string | null; note: string }[];
  priorities: { skill: string; priority: "high" | "medium" | "low"; why: string }[];
}
export interface Analysis {
  id: string; job_title: string; company: string | null; resume_id: string; resume_filename: string; score: number | null;
  user_adjusted: boolean; created_at: string; location?: string | null; experience_level?: string | null;
  extracted: { requirements: any[]; qualifications: { type: string; text: string }[]; responsibilities: string[] };
  requirements: { skill: string; level: Level }[]; comparison: Comparison;
}
export interface RoadmapTask { text: string; done: boolean }
export interface RoadmapItem {
  id: string; skill: string; category: string; priority: "high" | "medium" | "low"; why: string; status: "not_started" | "in_progress" | "completed";
  tasks: RoadmapTask[]; completed_at: string | null;
  content: { explanation: string; prerequisites: string[]; project_idea: string; resources: { title: string; url: string | null; note: string }[]; estimated_hours_min: number; estimated_hours_max: number; effort_note: string };
}
export interface Roadmap { id: string; analysis_id: string; title: string; created_at: string; progress: { total: number; completed: number; in_progress: number; percent: number }; items?: RoadmapItem[] }
export interface Application { id: string; company: string; job_title: string; job_url: string | null; status: string; applied_on: string | null; deadline: string | null; notes: string | null; analysis_id: string | null }
export const APPLICATION_STATUSES = ["SAVED", "APPLIED", "ASSESSMENT", "INTERVIEWING", "OFFER", "REJECTED", "WITHDRAWN"] as const;
