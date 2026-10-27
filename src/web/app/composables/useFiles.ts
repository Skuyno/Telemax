import type { Attachment, FileResponse } from '~/types/chat'

const attachmentCache = new Map<string, Promise<Attachment | null>>()
const linkCache = new Map<string, { url: string; expiresAt: number }>()
const LINK_REFRESH_MARGIN_MS = 30_000

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
    _retriedAfterRefresh = false,
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
      xhr.onload = async () => {
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
        } else if (xhr.status === 401 && !_retriedAfterRefresh) {
          // XHR bypasses useApi's ofetch instance (needed for upload
          // progress events), so it doesn't get the refresh-and-retry
          // handling for free — redone here, once, for this one request.
          const newToken = await refreshAccessToken()
          if (newToken) {
            uploadFile(chatId, file, onProgress, true).then(resolve, reject)
          } else {
            reject(new Error('Сессия истекла, войдите заново'))
          }
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

  async function getStreamUrl(fileId: string): Promise<string> {
    const cached = linkCache.get(fileId)
    if (cached && cached.expiresAt > Date.now() + LINK_REFRESH_MARGIN_MS) return cached.url

    const link = await api<{ url: string; expires_in: number }>(`/files/${fileId}/link`, {
      method: 'POST',
    })
    const url = `${config.public.apiBase}${link.url}`
    linkCache.set(fileId, { url, expiresAt: Date.now() + link.expires_in * 1000 })
    return url
  }

  async function getAttachmentInfo(fileId: string): Promise<Attachment | null> {
    const ready = attachmentCache.get(fileId)
    if (ready) return ready

    try {
      const url = await getStreamUrl(fileId)
      const probe = await fetch(url, { headers: { Range: 'bytes=0-0' } })
      if (!probe.ok && probe.status !== 206) return null

      const total = probe.headers.get('content-range')?.split('/')[1]
      return {
        id: fileId,
        name: nameFromDisposition(probe.headers.get('content-disposition')),
        type: probe.headers.get('content-type') ?? 'application/octet-stream',
        size: total ? Number(total) : 0,
        url,
      }
    } catch {
      return null
    }
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

  function refreshStreamUrl(fileId: string): Promise<string> {
    linkCache.delete(fileId)
    return getStreamUrl(fileId)
  }

  return { uploadFile, getAttachment, getAttachmentInfo, getStreamUrl, refreshStreamUrl }
}
