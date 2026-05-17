import { lazy, Suspense, type ReactNode } from 'react';
import type { RouteObject } from 'react-router-dom';
import { ProtectedRoute } from '@/app/routes/ProtectedRoute';
import { getRolesForModule } from '@/lib/roles.config';

const ShopFloorPage = lazy(() => import('./pages/ShopFloorPage'));
const JobCardsPage = lazy(() => import('./pages/JobCardsPage'));

const Loading = () => (
  <div className="flex h-48 items-center justify-center text-muted-foreground text-sm">
    Loading…
  </div>
);

const shopFloorRoles = getRolesForModule('shopFloor');
const shopFloorElement = (children: ReactNode) => (
  <ProtectedRoute allowedRoles={shopFloorRoles}>
    <Suspense fallback={<Loading />}>{children}</Suspense>
  </ProtectedRoute>
);

export const shopFloorRoutes: RouteObject[] = [
  {
    path: 'shop-floor',
    element: shopFloorElement(<ShopFloorPage />),
  },
  {
    path: 'shop-floor/:woId/job-cards',
    element: shopFloorElement(<JobCardsPage />),
  },
];
