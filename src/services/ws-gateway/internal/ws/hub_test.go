package ws

import "testing"

func TestBuildOutboundEvent(t *testing.T) {
	t.Run("message created", func(t *testing.T) {
		event := InboundEvent{
			ID: "m1", ChatID: "c1", SenderID: "u1", Body: "hi", CreatedAt: "t1",
			AttachmentFileIDs: []string{"f1", "f2"},
		}
		out, ok := buildOutboundEvent(subjectMessageCreated, event)
		if !ok {
			t.Fatal("expected ok=true")
		}
		if out.Type != "message.created" {
			t.Fatalf("expected type message.created, got %s", out.Type)
		}
		data, ok := out.Data.(MessageData)
		if !ok {
			t.Fatalf("expected MessageData, got %T", out.Data)
		}
		if data.MessageID != "m1" || data.Body != "hi" {
			t.Fatalf("unexpected data: %+v", data)
		}
		if len(data.AttachmentFileIDs) != 2 || data.AttachmentFileIDs[0] != "f1" {
			t.Fatalf("expected attachment_file_ids to survive, got %+v", data.AttachmentFileIDs)
		}
	})

	t.Run("message updated carries edited_at and attachment_file_ids", func(t *testing.T) {
		event := InboundEvent{
			ID: "m1", ChatID: "c1", Body: "edited", EditedAt: "t2",
			AttachmentFileIDs: []string{"f1"},
		}
		out, ok := buildOutboundEvent(subjectMessageUpdated, event)
		if !ok {
			t.Fatal("expected ok=true")
		}
		data := out.Data.(MessageData)
		if data.EditedAt == nil || *data.EditedAt != "t2" {
			t.Fatalf("expected edited_at=t2, got %+v", data.EditedAt)
		}
		if len(data.AttachmentFileIDs) != 1 || data.AttachmentFileIDs[0] != "f1" {
			t.Fatalf("expected attachment_file_ids to survive, got %+v", data.AttachmentFileIDs)
		}
	})

	t.Run("message deleted", func(t *testing.T) {
		event := InboundEvent{ID: "m1", ChatID: "c1", SenderID: "u1"}
		out, ok := buildOutboundEvent(subjectMessageDeleted, event)
		if !ok {
			t.Fatal("expected ok=true")
		}
		if out.Type != "message.deleted" {
			t.Fatalf("expected type message.deleted, got %s", out.Type)
		}
	})

	t.Run("message read", func(t *testing.T) {
		event := InboundEvent{ChatID: "c1", UserID: "u2", LastReadMessageID: "m9"}
		out, ok := buildOutboundEvent(subjectMessageRead, event)
		if !ok {
			t.Fatal("expected ok=true")
		}
		data := out.Data.(MessageReadData)
		if data.LastReadMessageID != "m9" {
			t.Fatalf("unexpected data: %+v", data)
		}
	})

	t.Run("typing", func(t *testing.T) {
		event := InboundEvent{ChatID: "c1", UserID: "u2"}
		out, ok := buildOutboundEvent(subjectTyping, event)
		if !ok {
			t.Fatal("expected ok=true")
		}
		if out.Type != "typing" {
			t.Fatalf("expected type typing, got %s", out.Type)
		}
	})

	t.Run("unknown subject", func(t *testing.T) {
		_, ok := buildOutboundEvent("chat.message.mystery", InboundEvent{})
		if ok {
			t.Fatal("expected ok=false for an unknown subject")
		}
	})
}
