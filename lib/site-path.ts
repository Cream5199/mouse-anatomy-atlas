// Runtime model paths (including those read from Digimouse metadata) and
// navigation use the same build-time base as Vite's bundled JS and CSS.
export const sitePath = (path: string) => import.meta.env.BASE_URL + path.replace(/^\/+/, '');
