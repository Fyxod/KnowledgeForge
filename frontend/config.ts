// Central frontend configuration.
// Development uses the standalone API. Production defaults to the page origin,
// allowing the bundled Nginx server to proxy REST and Socket.IO traffic.
const configuredApiUrl = (import.meta.env.VITE_API_URL as string | undefined)
  ?.trim()
  .replace(/\/$/, '');

export const API_URL = configuredApiUrl
  || (import.meta.env.DEV ? 'http://localhost:8000' : window.location.origin);

// Change these values to update project-wide settings
export const PROJECT_NAME = "Knowledge Synthesis Platform";

// Toggle whether the Sim (Strategic Intelligence Mesh) page is enabled. When true, root (/) and
// post-login redirect go to /sim. When false, root and post-login go to /dashboard
export const SIM_PAGE_ENABLED = false;
