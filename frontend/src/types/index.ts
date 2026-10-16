// Veřejné typy pro aplikaci. nor.ts je generovaný (npm run gen:types), tady jen aliasy.
import type { AINORInterniModelPripaduSmlouvaMeziModuly } from "./nor";

export type * from "./nor";

/** Kořen schématu: pacient + dokumenty + fakty + případ + audit. */
export type CaseBundle = AINORInterniModelPripaduSmlouvaMeziModuly;
