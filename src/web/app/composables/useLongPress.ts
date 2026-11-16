const LONG_PRESS_MS = 500
const MOVE_TOLERANCE_PX = 10

export function useLongPress(onMenu: (x: number, y: number) => void, onClick?: () => void) {
  let timer: ReturnType<typeof setTimeout> | undefined
  let start: { x: number; y: number } | null = null
  let suppressClick = false

  function cancel() {
    clearTimeout(timer)
    start = null
  }

  function onPointerDown(event: PointerEvent) {
    suppressClick = false
    if (event.pointerType !== 'touch') return
    start = { x: event.clientX, y: event.clientY }
    clearTimeout(timer)
    timer = setTimeout(() => {
      suppressClick = true
      if (start) onMenu(start.x, start.y)
    }, LONG_PRESS_MS)
  }

  function onPointerMove(event: PointerEvent) {
    if (!start) return
    if (Math.hypot(event.clientX - start.x, event.clientY - start.y) > MOVE_TOLERANCE_PX) cancel()
  }

  function onContextMenu(event: MouseEvent) {
    event.preventDefault()
    if (suppressClick) return
    onMenu(event.clientX, event.clientY)
  }

  function onClickCapture(event: MouseEvent) {
    if (!suppressClick) return
    suppressClick = false
    event.preventDefault()
    event.stopPropagation()
  }

  function handleClick() {
    if (suppressClick) {
      suppressClick = false
      return
    }
    onClick?.()
  }

  onBeforeUnmount(() => clearTimeout(timer))

  return {
    handleClick,
    onClickCapture,
    listeners: {
      pointerdown: onPointerDown,
      pointermove: onPointerMove,
      pointerup: cancel,
      pointercancel: cancel,
      contextmenu: onContextMenu,
    },
  }
}
