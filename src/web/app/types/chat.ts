export interface Chat {
  id: string
  title: string
  lastMessage?: Message
  unreadCount: number
}

export interface Message {
  id: string
  chatId: string
  senderId: string
  text: string
  createdAt: string
}
