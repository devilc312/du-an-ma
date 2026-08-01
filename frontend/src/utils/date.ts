export function toDateTimeLocal(value: string | null | undefined): string {
  if (!value) return ''
  const date = new Date(value)
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

export function toUtcIso(value: string | null | undefined): string | null {
  return value ? new Date(value).toISOString() : null
}

export function formatInTimezone(value: string, timezone: string): string {
  return new Intl.DateTimeFormat('vi-VN', {
    timeZone: timezone,
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}
