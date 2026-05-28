export const isDemoMode = import.meta.env.VITE_DEMO_MODE === "true";

/** Vite `base` — trailing slash included (e.g. `/repo-name/`) */
export const appBasePath = import.meta.env.BASE_URL;

export const routerBasename =
  appBasePath === "/" ? undefined : appBasePath.replace(/\/$/, "");
