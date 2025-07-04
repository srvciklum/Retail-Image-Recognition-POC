const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
const API_VERSION = "api/v1";

export const API_CONFIG = {
  baseUrl: API_BASE_URL,
  apiPrefix: API_VERSION,
  getFullUrl: (path: string) => `${API_BASE_URL}/${API_VERSION}${path.startsWith("/") ? path : `/${path}`}`,
};
