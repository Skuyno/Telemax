/** «Полина Смирнова» → «ПС», «polina_test» → «PT», «kseteny» → «KS». */
export function toInitials(name: string): string {
  const parts = name.split(/[\s_.-]+/).filter(Boolean)
  const letters = parts.length > 1 ? parts[0]![0]! + parts[1]![0]! : name.slice(0, 2)
  return letters.toUpperCase()
}
