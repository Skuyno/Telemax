export interface ChatPreview {
  body: string
  createdAt: string
  authorLabel?: string
}

export interface Chat {
  id: string
  title: string
  initials: string
  lastMessage?: ChatPreview
}

export interface Message {
  id: string
  chatId: string
  senderId: string
  body: string
  createdAt: string
}
