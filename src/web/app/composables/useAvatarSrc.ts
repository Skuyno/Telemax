const cache = new Map<string, Promise<string | null>>()

export function useAvatarSrc(url: () => string | null | undefined) {
  const api = useApi()
  const src = ref<string | null>(null)

  watch(
    url,
    async (value) => {
      src.value = null
      if (!value) return

      let pending = cache.get(value)
      if (!pending) {
        pending = api<Blob>(value, { responseType: 'blob' })
          .then((blob) => URL.createObjectURL(blob))
          .catch(() => {
            cache.delete(value)
            return null
          })
        cache.set(value, pending)
      }

      const resolved = await pending
      if (url() === value) src.value = resolved
    },
    { immediate: true },
  )

  return src
}
