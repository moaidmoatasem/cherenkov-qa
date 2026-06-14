import {
  createPlugin,
  createApiFactory,
  discoveryApiRef,
  createRoutableExtension,
} from '@backstage/core-plugin-api';
import { CherenkovClient, cherenkovApiRef } from './api/CherenkovClient';

export const cherenkovPlugin = createPlugin({
  id: 'cherenkov',
  apis: [
    createApiFactory({
      api: cherenkovApiRef,
      deps: { discoveryApi: discoveryApiRef },
      factory: ({ discoveryApi }) => new CherenkovClient({ discoveryApi }),
    }),
  ],
});

export const CherenkovPage = cherenkovPlugin.provide(
  createRoutableExtension({
    name: 'CherenkovPage',
    component: () => import('./components/ViolationTable').then(m => m.ViolationTable),
    mountPoint: 'entity.content.cherenkov',
  }),
);
