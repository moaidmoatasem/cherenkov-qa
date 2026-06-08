export const ROUTES = {
  projects: '/',
  setup: '/setup',
  pipeline: '/pipeline',
  review: '/review',
  healing: '/healing',
  eject: '/eject',
  overview: '/overview',
  truthMap: '/truth-map',
  divergences: '/divergences',
  explore: '/explore',
  author: '/author',
  signals: '/signals',
  governance: '/governance',
  memory: '/memory',
  chat: '/chat',
  settings: '/settings',
  uiKit: '/ui-kit',
} as const;

export type RouteKey = keyof typeof ROUTES;
