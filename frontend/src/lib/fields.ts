// Metadata polí NOR pro UI: české popisky a rozdělení do sekcí jako v originálním formuláři.
// Povinnost a číselník se berou ze schématu (x-nor-fields), aby se nerozcházely.
import schema from "../../../schema/nor_case.schema.json";
import type { NorFieldName } from "../types";

type XNorField = { required_in_xsd: boolean; codelist: string | null };
const X_NOR = schema.$defs.NorFieldName["x-nor-fields"] as Record<NorFieldName, XNorField>;

export const FIELD_NAMES = schema.$defs.NorFieldName.enum as NorFieldName[];

export const FIELD_LABELS: Record<NorFieldName, string> = {
  hzz: "Zařízení (pracoviště)",
  hodd: "Oddělení",
  rodcis: "Rodné číslo",
  pohlavi: "Pohlaví",
  dat_nar: "Datum narození",
  obec: "Obec bydliště",
  zeme: "Země původu",
  cizinec: "Cizinec",
  bezdomovec: "Neznámo (bezdomovec, neudaný pobyt)",
  dat_dg: "Datum stanovení diagnózy",
  dg_stan: "K dg. vedla tato vyšetření",
  lateralita: "Lateralita",
  dg_nov: "Dg. MKN",
  dg_nov_slovne: "Dg. slovně",
  topo: "Topografie",
  morfo_metoda: "Typ morfologie",
  morfo: "Kód morfologie",
  morfo_slovne: "Název morfologie",
  grade: "Grading",
  t: "T",
  n: "N",
  m: "M",
  ptnmy: "y (po neoadjuvanci)",
  pt: "pT",
  pn: "pN",
  pvu: "pN vyšetřené uzliny",
  ppu: "pN pozitivní uzliny",
  psu: "sn (sentinelová uzlina)",
  pm: "pM",
  metastaze: "Lokalizace vzdálených metastáz",
  trofoblast: "Riziková kategorie",
  serove_markery: "Sérové nádorové markery",
  p16: "p16 pozitivní",
  stadium: "Klinické stadium",
  rozsah: "Onemocnění",
  pozn: "Poznámka",
  hdatum: "Datum hlášení",
  lekar: "Jméno hlásícího lékaře",
  htyp: "Pracoviště hlásící novotvar",
  idzz: "ID zdravotnického zařízení",
};

export const SECTIONS: { title: string; fields: NorFieldName[] }[] = [
  {
    title: "Diagnostická část",
    fields: ["hzz", "hodd", "rodcis", "pohlavi", "dat_nar", "obec", "zeme", "cizinec", "bezdomovec"],
  },
  { title: "Diagnóza", fields: ["dat_dg", "dg_stan", "lateralita", "dg_nov", "dg_nov_slovne", "topo"] },
  { title: "Morfologie", fields: ["morfo_metoda", "morfo", "morfo_slovne", "grade"] },
  {
    title: "TNM",
    fields: [
      "t", "n", "m", "ptnmy", "pt", "pn", "pvu", "ppu", "psu", "pm",
      "metastaze", "trofoblast", "serove_markery", "p16", "stadium",
    ],
  },
  { title: "Ostatní", fields: ["rozsah", "pozn"] },
  { title: "Hlášení", fields: ["hdatum", "lekar", "htyp", "idzz"] },
];

export function isRequired(field: NorFieldName): boolean {
  return X_NOR[field]?.required_in_xsd ?? false;
}

export function codelistOf(field: NorFieldName): string | null {
  return X_NOR[field]?.codelist ?? null;
}
