import { useEffect, useState } from 'react'
import { Card, Button, Input } from '../components/ui'
import { useAuth } from '../hooks/useAuth'
import { usersApi } from '../api/users'
import { getErrorMessage } from '../api/client'

const timezones = ['Asia/Ho_Chi_Minh', 'Asia/Bangkok', 'Asia/Singapore', 'Asia/Tokyo', 'UTC', 'America/Los_Angeles', 'America/New_York', 'Europe/London', 'Europe/Paris']

export function ProfilePage() {
  const { user, refreshUser } = useAuth(); const [name, setName] = useState(''); const [timezone, setTimezone] = useState('Asia/Ho_Chi_Minh')
  const [saved, setSaved] = useState(false); const [saving, setSaving] = useState(false); const [error, setError] = useState('')
  useEffect(() => { if (user) { setName(user.full_name); setTimezone(user.timezone) } }, [user])
  const save = async () => { if (name.trim().length < 2) { setError('Họ và tên phải có ít nhất 2 ký tự.'); return }; setSaving(true); setError(''); try { await usersApi.updateProfile({ full_name: name.trim(), timezone }); await refreshUser(); setSaved(true); window.setTimeout(() => setSaved(false), 2000) } catch (reason) { setError(getErrorMessage(reason, 'Không thể lưu hồ sơ.')) } finally { setSaving(false) } }
  return <div className="mx-auto max-w-2xl"><h1 className="text-3xl font-bold">Hồ sơ</h1><p className="mt-2 text-slate-500">Quản lý thông tin và múi giờ nhắc việc.</p><Card className="mt-6 space-y-5"><label className="block text-sm font-medium">Email<Input className="mt-1.5 bg-slate-50" value={user?.email ?? ''} disabled /></label><label className="block text-sm font-medium">Họ và tên<Input className="mt-1.5" value={name} onChange={e => setName(e.target.value)} /></label><label className="block text-sm font-medium">Múi giờ<select className="mt-1.5 min-h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm" value={timezone} onChange={e => setTimezone(e.target.value)}>{timezones.map(item => <option key={item} value={item}>{item}</option>)}</select></label>{error && <p role="alert" className="rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}<div className="flex items-center gap-3"><Button onClick={() => void save()} disabled={saving}>{saving ? 'Đang lưu…' : 'Lưu thay đổi'}</Button>{saved && <span className="text-sm text-emerald-600">Đã lưu</span>}</div></Card></div>
}
