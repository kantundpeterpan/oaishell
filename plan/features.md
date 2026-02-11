# Features to implement

## [P1] Default action

It should be possible to define default command in the yaml which is called each time on ENTER. This could be either an API method or a custum defined method.

## [P1] Response formatting

conditional/optional extraction

arbitrary combintaions of response fields, each of which can be formatted in a nice and different way

- tables
- markdown
- selections

- Response panel header

## Ctrl-C for commandline clearing, double for exiting

Ctrl-C should result in clearing the command line, double Ctrl-C in exti

## Short alias for /operations-tui

In the hierarchical /operations-tui view not the complete operation id should be shown but rather the truncated path.

The truncated path excludes the common prefix and the tag, i.e.

/api/v1/chat/settings/change -> settings/change
/api/v1/chat/{session_id}/events/listen -> {session_id}/events/listen

This should be implemented in simultenously with a review of the aggregation_depth configuration.

`aggregration_depth` should be applied AFTER removing the common prefix and the tag, i.e. (from the table below):

chat:
  - /emotion
  - /dropdown


etc.

The edge case where prefix/tag is an exposed endpoint has to be handled.


┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Operation ID                                                     ┃ Method ┃ Path                                    ┃ Summary                   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ health_check_api_v1_health_get                                   │ GET    │ /api/v1/health                          │ Health Check              │
│ initialize_chat_api_v1_chat_init_post                            │ POST   │ /api/v1/chat/init                       │ Initialize Chat           │
│ handle_message_api_v1_chat_post                                  │ POST   │ /api/v1/chat                            │ Handle Message            │
│ handle_emotion_selection_api_v1_chat_emotion_post                │ POST   │ /api/v1/chat/emotion                    │ Handle Emotion Selection  │
│ handle_dropdown_selection_api_v1_chat_dropdown_post              │ POST   │ /api/v1/chat/dropdown                   │ Handle Dropdown Selection │
│ delete_user_summary_api_v1_chat_delete_post                      │ POST   │ /api/v1/chat/delete                     │ Delete User Summary       │
│ change_settings_api_v1_chat_settings_change_post                 │ POST   │ /api/v1/chat/settings/change            │ Change Settings           │
│ stream_session_events_api_v1_chat__session_id__events_listen_get │ GET    │ /api/v1/chat/{session_id}/events/listen │ Stream Session Events     │
│ push_session_event_api_v1_chat__session_id__events_push_post     │ POST   │ /api/v1/chat/{session_id}/events/push   │ Push Session Event        │
│ transcribe_audio_api_v1_audio_transcribe_post                    │ POST   │ /api/v1/audio/transcribe                │ Transcribe Audio          │
│ upload_files_api_v1_files_upload_post                            │ POST   │ /api/v1/files/upload                    │ Upload Files              │
│ get_file_api_v1_files__filename__get                             │ GET    │ /api/v1/files/{filename}                │ Get File                  │
│ delete_file_api_v1_files__filename__delete                       │ DELETE │ /api/v1/files/{filename}                │ Delete File               │
│ get_session_feedback_api_v1_feedback__session_id__get            │ GET    │ /api/v1/feedback/{session_id}           │ Get Session Feedback      │
│ submit_feedback_api_v1_feedback__session_id__post                │ POST   │ /api/v1/feedback/{session_id}           │ Submit Feedback           │
│ delete_session_feedback_api_v1_feedback__session_id__delete      │ DELETE │ /api/v1/feedback/{session_id}           │ Delete Session Feedback   │

## Headers

## Secrets

${{ secrets.value }} or ${{ env.value }} templating in the yaml should be implemmented for increased security
Sensible data received and stored from a response should not be publicly visible

## Acces to state variables

State variables should be accessible and writable in different ways:

1) implement /state set <key> <value> and /state get <key>
2) $state.key or {$state.key} should be availabe in the command line to access values currently stored in state

## Request autofill

Missing request parameters (path, body, query) should be looked up in state and used if found. This should be default behaviour and not needed to be configured in the yaml.
Notificationi of parameter autofill should be similar to that of saving values to state from response.

## Autocomplete for custom slash commands

## Listing of custom methods

## Autocompletion for /call <tag> -> ...

## [P3] Streaming response handling

SSEs should be handled in a non blocking way if necessary