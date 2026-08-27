# Experiment: Burmese speech-to-text for recipe videos

## Objective

Select a speech-to-text engine for Burmese cooking narration. Two cloud APIs were compared: **Google Cloud Speech-to-Text** and **ElevenLabs Scribe**.

## Setup

Both engines transcribed the same audio bytes. ffmpeg extracted 16 kHz mono PCM from a local copy of the source reel (64.2 s). That PCM was split into 55-second chunks (Google’s synchronous recognize limit). Each engine received those chunks in order; timestamps were offset by chunk index.

| Item | Value |
|---|---|
| Source | [Facebook reel](https://www.facebook.com/reel/1033484732739023) (Burmese fish recipe) |
| Language | Burmese |
| Audio | ffmpeg, mono, 16 kHz, LINEAR16 PCM, in memory |
| Chunks | 55 s, then remainder (~9 s); shared by both engines |
| Credentials | API keys from project `.env` |
| Outputs | `benchmark/speech to text/transcripts/test1_{engine}.txt` |

Shared extract and chunking live in `audio.py`.

### Google Speech-to-Text (`STT_test_googleSTT.py`)

- Endpoint: `speech:recognize` (synchronous)
- Payload: the shared LINEAR16 PCM chunk
- Language code: `my-MM` (API BCP-47)
- Automatic punctuation enabled
- Timestamps from each result’s `resultEndTime`, plus chunk offset

### ElevenLabs Scribe (`STT_test_elevenlabs.py`)

- Endpoint: `/v1/speech-to-text`
- Model: `scribe_v2`
- Payload: the same PCM chunk wrapped as a WAV header (no re-encode)
- Language code: `mya` (API code for Burmese)
- Word-level timestamps; lines split on pauses ≥ 0.8 s, plus chunk offset

Language-code strings and timestamp formatting are API-required. The audio content and chunk boundaries are identical.

## Result

ElevenLabs returned a coherent Burmese transcript of the narration, with usable timestamps. Google returned jammed, largely unreadable text on the same chunks (one long unsegmented span plus a short English fragment). Splitting at 55 s cut ElevenLabs mid-utterance in the second chunk; the first chunk stayed readable. Google failed on both chunks.

## Decision

Use **ElevenLabs Scribe v2** for Burmese recipe narration.
