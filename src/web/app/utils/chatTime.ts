const WEEKDAYS_SHORT = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб']

function startOfDay(date: Date): number {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime()
}

export function formatMessageTime(iso: string): string {
  const date = new Date(iso)
  return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
}

export function formatChatListTime(iso: string): string {
  const date = new Date(iso)
  const dayDiff = Math.round((startOfDay(new Date()) - startOfDay(date)) / 86_400_000)

  if (dayDiff <= 0) return formatMessageTime(iso)
  if (dayDiff === 1) return 'вчера'
  if (dayDiff < 7) return WEEKDAYS_SHORT[date.getDay()] ?? ''
  return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' })
}

export function formatDateSeparator(iso: string): string {
  const date = new Date(iso)
  const dayDiff = Math.round((startOfDay(new Date()) - startOfDay(date)) / 86_400_000)

  if (dayDiff <= 0) return 'Сегодня'
  if (dayDiff === 1) return 'Вчера'
  return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })
}

export function dayKey(iso: string): string {
  return new Date(iso).toDateString()
}
