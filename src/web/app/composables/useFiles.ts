import type { Attachment, FileResponse } from '~/types/chat'

const attachmentCache = new Map<string, Promise<Attachment | null>>()

function decodeName(raw: string): string {
  try {
    return decodeURIComponent(raw)
  } catch {
    return raw
  }
}

function nameFromDisposition(header: string | null): string {
  const match = header?.match(/filename="?([^";]+)"?/i)
  return match ? decodeName(match[1]!) : 'Файл'
}

export function useFiles() {
  const api = useApi()
  const config = useRuntimeConfig()
  const auth = useAuthStore()

  function uploadFile(
    chatId: string,
    file: File,
    onProgress: (fraction: number) => void,
  ): Promise<FileResponse> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest()
      xhr.open('POST', `${config.public.apiBase}/files?chat_id=${encodeURIComponent(chatId)}`)
      if (auth.accessToken) xhr.setRequestHeader('Authorization', `Bearer ${auth.accessToken}`)
      xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream')
      xhr.setRequestHeader('X-Filename', encodeURIComponent(file.name))

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) onProgress(event.loaded / event.total)
      }
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          const saved = JSON.parse(xhr.responseText) as FileResponse
          attachmentCache.set(
            saved.id,
            Promise.resolve({
              id: saved.id,
              name: file.name,
              type: file.type,
              size: file.size,
              url: URL.createObjectURL(file),
            }),
          )
          resolve(saved)
        } else if (xhr.status === 413) {
          reject(new Error('Файл слишком большой'))
        } else {
          reject(new Error('Не удалось загрузить файл'))
        }
      }
      xhr.onerror = () => reject(new Error('Не удалось загрузить файл'))
      xhr.send(file)
    })
  }

  function getAttachment(fileId: string): Promise<Attachment | null> {
    let pending = attachmentCache.get(fileId)
    if (!pending) {
      pending = api
        .raw<Blob>(`/files/${fileId}`, { responseType: 'blob' })
        .then((response) => {
          const blob = response._data!
          return {
            id: fileId,
            name: nameFromDisposition(response.headers.get('content-disposition')),
            type: blob.type,
            size: blob.size,
            url: URL.createObjectURL(blob),
          }
        })
        .catch(() => {
          attachmentCache.delete(fileId)
          return null
        })
      attachmentCache.set(fileId, pending)
    }
    return pending
  }

  return { uploadFile, getAttachment }
}
