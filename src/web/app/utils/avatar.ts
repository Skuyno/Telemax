export const AVATAR_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
export const AVATAR_MAX_BYTES = 5 * 1024 * 1024

export function avatarFileError(file: File): string {
  if (!AVATAR_TYPES.includes(file.type)) return 'Подойдёт картинка в формате JPG, PNG, WEBP или GIF'
  if (file.size > AVATAR_MAX_BYTES) return 'Файл больше 5 МБ — выберите картинку поменьше'
  return ''
}
