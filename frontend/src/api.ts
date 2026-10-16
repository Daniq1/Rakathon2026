// Zdroj dat. Řez 1: statická ukázka (examples/pacient1_case.example.json doplněná o text PDF,
// viz scripts/build_demo_case.py). Řez 3: nahradit voláními GET /api/patients a /api/cases/{id}.
import pacient1 from "./mock/pacient1.case.json";
import mkn10 from "./mock/mkn10_novotvary.json";
import type { CaseBundle } from "./types";

export type CodelistItem = { code: string; dotted: string; label: string };

export async function loadCases(): Promise<CaseBundle[]> {
  return [structuredClone(pacient1 as unknown as CaseBundle)];
}

/** Našeptávač pro pole s číselníkem, který máme k dispozici (zatím jen MKN-10 novotvary). */
export function codelistFor(codelist: string | null): CodelistItem[] | null {
  if (codelist === "MKN10_5") return mkn10 as CodelistItem[];
  return null;
}

export type UploadedFile = { name: string; size: number; uploadedAt: string };

/** Řez 1 bez backendu: soubory se jen evidují v paměti. Řez 2/3: POST /api/documents. */
export async function uploadDocuments(files: File[]): Promise<UploadedFile[]> {
  const now = new Date().toISOString();
  return files.map((f) => ({ name: f.name, size: f.size, uploadedAt: now }));
}
