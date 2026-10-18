package ws

import (
	"encoding/json"
	"reflect"
	"testing"
)

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

	t.Run("chat sync required", func(t *testing.T) {
		event := InboundEvent{ChatID: "c1", Reason: "members_added"}
		out, ok := buildOutboundEvent(subjectChatSync, event)
		if !ok {
			t.Fatal("expected ok=true")
		}
		if out.Type != "chat.sync_required" {
			t.Fatalf("unexpected type: %s", out.Type)
		}
		data, ok := out.Data.(ChatSyncData)
		if !ok {
			t.Fatalf("expected ChatSyncData, got %T", out.Data)
		}
		if data.ChatID != "c1" || data.Reason != "members_added" {
			t.Fatalf("unexpected data: %+v", data)
		}
	})

	t.Run("unknown subject", func(t *testing.T) {
		_, ok := buildOutboundEvent("chat.message.mystery", InboundEvent{})
		if ok {
			t.Fatal("expected ok=false for an unknown subject")
		}
	})
}

func TestChatSyncFanout(t *testing.T) {
	for _, reason := range []string{"created", "updated", "members_added", "member_removed"} {
		t.Run(reason, func(t *testing.T) {
			hub := NewHub(nil, nil)
			clients := map[string]*Client{
				"owner tab 1": {send: make(chan []byte, 1)},
				"owner tab 2": {send: make(chan []byte, 1)},
				"member":      {send: make(chan []byte, 1)},
				"removed":     {send: make(chan []byte, 1)},
				"outsider":    {send: make(chan []byte, 1)},
			}
			hub.users["owner"] = map[*Client]struct{}{
				clients["owner tab 1"]: {}, clients["owner tab 2"]: {},
			}
			for _, userID := range []string{"member", "removed", "outsider"} {
				hub.users[userID] = map[*Client]struct{}{clients[userID]: {}}
			}
			payload, err := json.Marshal(map[string]interface{}{
				"chat_id": "c1", "reason": reason,
				"recipient_ids": []string{"owner", "member", "removed", "offline"},
			})
			if err != nil {
				t.Fatal(err)
			}
			hub.HandleNatsEvent(subjectChatSync, payload)
			want := map[string]interface{}{
				"type": "chat.sync_required",
				"data": map[string]interface{}{"chat_id": "c1", "reason": reason},
			}
			for name, client := range clients {
				select {
				case frame := <-client.send:
					if name == "outsider" {
						t.Fatal("sync leaked to a user outside recipient_ids")
					}
					var got map[string]interface{}
					if err := json.Unmarshal(frame, &got); err != nil {
						t.Fatal(err)
					}
					if !reflect.DeepEqual(got, want) {
						t.Fatalf("%s: frame = %s, want %+v", name, frame, want)
					}
				default:
					if name != "outsider" {
						t.Fatalf("%s did not receive sync", name)
					}
				}
			}
		})
	}
}

func TestChatSyncIgnoresInvalidEvents(t *testing.T) {
	for _, tc := range []struct {
		name, subject, payload string
	}{
		{"malformed JSON", subjectChatSync, `{`},
		{"invalid recipients", subjectChatSync, `{"recipient_ids":42}`},
		{"no recipients", subjectChatSync, `{"chat_id":"c1","reason":"created"}`},
		{"unknown subject", "chat.unknown", `{"recipient_ids":["u1"]}`},
	} {
		t.Run(tc.name, func(t *testing.T) {
			hub := NewHub(nil, nil)
			client := &Client{send: make(chan []byte, 1)}
			hub.users["u1"] = map[*Client]struct{}{client: {}}
			hub.HandleNatsEvent(tc.subject, []byte(tc.payload))
			if len(client.send) != 0 {
				t.Fatal("unexpected frame for an ignored event")
			}
		})
	}
}
