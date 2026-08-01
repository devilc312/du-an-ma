import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
export function ProtectedRoute() { const { user, loading } = useAuth(); const location = useLocation(); if (loading) return <div className="grid min-h-screen place-items-center">Đang tải…</div>; return user ? <Outlet /> : <Navigate to="/login" replace state={{ from: location }} /> }
export function AdminRoute() { const { user } = useAuth(); return user?.roles.includes('admin') ? <Outlet /> : <Navigate to="/app" replace /> }
