import { isDemoMode } from "../config/env";
import { liveApi } from "./client";
import { mockApi } from "./mock";

export const api = isDemoMode ? mockApi : liveApi;

export type { DateFilter, Granularity } from "./types";
