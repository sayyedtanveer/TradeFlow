import { lazy, Suspense } from 'react';
import type { RouteObject } from 'react-router-dom';

const ShopFloorPage = lazy(() => import('./pages/ShopFloorPage'));
const JobCardsPage = lazy(() => import('./pages/JobCardsPage'));

const Loading = () => (
  <div className="flex h-48 items-center justify-center text-muted-foreground text-sm">
    Loading…
  </div>
);

export const shopFloorRoutes: RouteObject[] = [
  {
    path: 'shop-floor',
    element: (
      <Suspense fallback={<Loading />}>
        <ShopFloorPage />
      </Suspense>
    ),
  },
  {
    path: 'shop-floor/:woId/job-cards',
    element: (
      <Suspense fallback={<Loading />}>
        <JobCardsPage />
      </Suspense>
    ),
  },
];
