import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { useAuth } from '../hooks/useAuth'
import { Button, Input } from '../components/ui'
import { getErrorMessage } from '../api/client'
import { useState } from 'react'
const schema = z.object({ email: z.email('Email không hợp lệ'), password: z.string().min(8, 'Mật khẩu tối thiểu 8 ký tự') })
type FormValues = z.infer<typeof schema>
export function LoginPage() { const { login } = useAuth(); const navigate = useNavigate(); const location = useLocation(); const [error, setError] = useState(''); const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({ resolver: zodResolver(schema) }); const submit = async (values: FormValues) => { try { await login(values); navigate((location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? '/app', { replace: true }) } catch (reason) { setError(getErrorMessage(reason, 'Không thể đăng nhập.')) } }; return <div><h1 className="text-3xl font-bold">Chào mừng trở lại</h1><p className="mt-2 text-slate-500">Đăng nhập để tiếp tục với kế hoạch của bạn.</p><form onSubmit={handleSubmit(submit)} className="mt-8 space-y-5"><label className="block text-sm font-medium">Email<Input className="mt-1.5" type="email" autoComplete="email" {...register('email')} /></label>{errors.email && <p className="-mt-4 text-sm text-rose-600">{errors.email.message}</p>}<label className="block text-sm font-medium">Mật khẩu<Input className="mt-1.5" type="password" autoComplete="current-password" {...register('password')} /></label>{errors.password && <p className="-mt-4 text-sm text-rose-600">{errors.password.message}</p>}{error && <p role="alert" className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}<Button className="w-full" disabled={isSubmitting}>{isSubmitting ? 'Đang đăng nhập…' : 'Đăng nhập'}</Button></form><p className="mt-6 text-center text-sm text-slate-500">Chưa có tài khoản? <Link className="font-semibold text-indigo-600" to="/register">Tạo tài khoản</Link></p></div> }
