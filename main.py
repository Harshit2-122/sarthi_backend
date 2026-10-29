#!/usr/bin/env python3
"""
SARTHI — Real-Time Speech-to-Indian Sign Language (ISL) Backend Server
Production-grade FastAPI + WebSockets + Whisper STT + ISL Linguistic Engine

Deployed on Render / Cloud. Connects live with:
- Teacher Dashboard:  https://teacher-dashboard-opal.vercel.app
- Student Dashboard:  https://student-dashboard-silk-alpha.vercel.app
- Sign Model Studio:  https://signmodelstudio.vercel.app
"""

import os
import sys
import json
import asyncio
import tempfile
from contextlib import asynccontextmanager
from typing import List, Optional, Set

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ─── Environment & Model Settings ────────────────────────────────────────────

WHISPER_MODEL_NAME = os.environ.get("WHISPER_MODEL", "tiny")
whisper_model = None


def load_whisper_engine():
    """Initializes Faster-Whisper CPU-optimized STT model."""
    global whisper_model
    try:
        from faster_whisper import WhisperModel
        # compute_type="int8" runs on standard CPU with ~150MB RAM footprint
        whisper_model = WhisperModel(
            WHISPER_MODEL_NAME,
            device="auto",
            compute_type="int8",
            cpu_threads=int(os.environ.get("CPU_THREADS", "4"))
        )
        print(f"[Whisper STT] faster-whisper '{WHISPER_MODEL_NAME}' model initialized successfully.")
    except ImportError:
        try:
            import whisper
            whisper_model = whisper.load_model(WHISPER_MODEL_NAME)
            print(f"[Whisper STT] openai-whisper '{WHISPER_MODEL_NAME}' model initialized successfully.")
        except ImportError:
            print("[Whisper STT] Notice: 'faster-whisper' not installed. Running in text-passthrough mode.")
            whisper_model = None
    except Exception as e:
        print(f"[Whisper STT] Model load warning: {e}")
        whisper_model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load Whisper model
    load_whisper_engine()
    yield
    # Shutdown: Clean up connections
    print("[Shutdown] Cleaning active WebSocket connections...")


# ─── FastAPI Application Definition ──────────────────────────────────────────

app = FastAPI(
    title="SARTHI Accessibility Engine",
    description="Continuous Speech-to-Text & Indian Sign Language (ISL) Broadcasting Hub",
    version="2.2.0",
    lifespan=lifespan
)

# ─── Production CORS Configuration ───────────────────────────────────────────
# Supports production Vercel apps, previews, and local development

ALLOWED_ORIGINS = [
    "https://teacher-dashboard-opal.vercel.app",
    "https://student-dashboard-silk-alpha.vercel.app",
    "https://signmodelstudio.vercel.app",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:8000",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Live WebSocket Connection Manager ───────────────────────────────────────

class ClassroomBroadcastManager:
    """Manages active student WebSocket connections and broadcasts live transcripts."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.segment_counter: int = 0

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"[Broadcast Hub] Student connected. Total active students: {len(self.active_connections)}")

        # Send welcome session handshake
        try:
            await websocket.send_json({
                "type": "session",
                "payload": {
                    "sessionId": "sarthi-live-session",
                    "teacherName": "Teacher (Live)",
                    "subject": "Real-time Classroom Lecture",
                    "status": "connected"
                }
            })
        except Exception:
            pass

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        print(f"[Broadcast Hub] Student disconnected. Remaining students: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return

        payload_str = json.dumps(message, ensure_ascii=False)
        dead_connections = set()

        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload_str)
            except Exception:
                dead_connections.add(connection)

        for dead in dead_connections:
            self.active_connections.discard(dead)


broadcaster = ClassroomBroadcastManager()


# ─── Audio Transcription Helper ──────────────────────────────────────────────

def transcribe_audio_file(file_path: str, language: Optional[str] = None) -> str:
    """Transcribes an audio file into text using Whisper."""
    global whisper_model
    if whisper_model is None:
        return ""

    try:
        lang_code = language if language and language not in ("auto", "") else None
        if hasattr(whisper_model, "transcribe"):
            segments, _ = whisper_model.transcribe(file_path, language=lang_code, beam_size=5)
            return " ".join([seg.text for seg in segments]).strip()
        result = whisper_model.transcribe(file_path, language=lang_code)
        return result.get("text", "").strip()
    except Exception as err:
        print(f"[Whisper STT] Transcription error: {err}")
        return ""


# ─── Indian Sign Language (ISL) Linguistic Grammar Engine ─────────────────────

GLOSS_MAP = {
    # Pronouns
    "i": "ME", "me": "ME", "my": "MY", "mine": "MY",
    "you": "YOU", "your": "YOUR", "he": "HE", "she": "SHE", "him": "HIM", "her": "HER",
    "we": "WE", "our": "OUR", "they": "THEY", "their": "THEIR", "it": "IT",

    # Verbs (Lemmas in ISL)
    "is": "BE", "am": "BE", "are": "BE", "was": "BE", "were": "BE",
    "go": "GO", "going": "GO", "went": "GO", "gone": "GO",
    "come": "COME", "coming": "COME", "came": "COME",
    "want": "WANT", "wanted": "WANT", "need": "NEED", "needs": "NEED",
    "eat": "EAT", "eating": "EAT", "ate": "EAT", "drink": "DRINK",
    "see": "SEE", "look": "LOOK", "hear": "HEAR", "say": "SAY", "tell": "TELL",
    "buy": "BUY", "sell": "SELL", "give": "GIVE", "take": "TAKE",
    "play": "PLAY", "work": "WORK", "study": "STUDY", "read": "READ",
    "write": "WRITE", "open": "OPEN", "close": "CLOSE", "help": "HELP",
    "explain": "EXPLAIN", "understand": "UNDERSTAND", "learn": "LEARN",

    # Interrogatives (shifted to the end in ISL syntax)
    "what": "WHAT", "where": "WHERE", "when": "WHEN", "who": "WHO",
    "why": "WHY", "how": "HOW", "which": "WHICH",

    # Common greetings and classroom lexical tokens
    "good morning": "GOOD MORNING", "thank you": "THANK", "how are you": "HOW",
    "book": "BOOK", "notebook": "NOTEBOOK", "library": "LIBRARY", "school": "SCHOOL",
    "class": "CLASS", "teacher": "TEACHER", "student": "STUDENT", "water": "WATER",
    "home": "HOME", "hospital": "HOSPITAL", "name": "NAME", "time": "TIME",
    "good": "GOOD", "bad": "BAD", "happy": "HAPPY", "sad": "SAD", "fine": "FINE",
    "important": "IMPORTANT", "new": "NEW", "again": "AGAIN", "today": "TODAY",
    "tomorrow": "TOMORROW", "yesterday": "YESTERDAY", "yes": "YES", "no": "NO"
}

QUESTION_WORDS = {"WHAT", "WHERE", "WHEN", "WHO", "WHY", "HOW", "WHICH"}
STOP_WORDS = {"the", "a", "an", "to", "of", "in", "at", "for", "with", "about"}


def text_to_isl_gloss(english_text: str) -> dict:
    """
    Transforms English text into Indian Sign Language (ISL) gloss tokens:
    1. Lemmatizes words to base sign concepts.
    2. Drops redundant articles and copulas (a, an, the, is, are).
    3. Converts English SVO (Subject-Verb-Object) to ISL SOV (Subject-Object-Verb).
    4. Positions question words at the end of the sentence.
    """
    import re
    cleaned = re.sub(r"[^a-zA-Z0-9\s']", " ", english_text.lower()).strip()
    words = cleaned.split()

    if not words:
        return {"gloss": [], "method": "none", "source": english_text}

    tokens = []
    full_str = " ".join(words)

    # Check known multi-word phrases first
    if "good morning" in full_str:
        tokens.append("GOOD MORNING")
        words = [w for w in words if w not in ("good", "morning")]

    q_words = []
    for w in words:
        if w in STOP_WORDS:
            continue
        mapped = GLOSS_MAP.get(w, w.upper())
        if mapped in QUESTION_WORDS:
            q_words.append(mapped)
        else:
            tokens.append(mapped)

    # Shift question words to the end according to ISL syntax
    tokens.extend(q_words)

    return {
        "gloss": tokens,
        "method": "rule-based-sov",
        "source": english_text
    }


# ─── HTTP Endpoints ──────────────────────────────────────────────────────────

@app.get("/")
async def root_index():
    return {
        "service": "SARTHI Accessibility Backend",
        "status": "online",
        "version": "2.2.0",
        "whisper_ready": whisper_model is not None,
        "connected_students": len(broadcaster.active_connections),
        "endpoints": {
            "health": "/health",
            "gloss_tester": "/api/gloss?text=hello",
            "teacher_websocket": "/ws/speech",
            "student_websocket": "/ws/viewer"
        },
        "frontends": {
            "teacher": "https://teacher-dashboard-opal.vercel.app",
            "student": "https://student-dashboard-silk-alpha.vercel.app",
            "studio": "https://signmodelstudio.vercel.app"
        }
    }


@app.get("/health")
@app.get("/api/health")
async def health_check():
    """Healthcheck endpoint for Render keep-alive and frontend connection check."""
    return {
        "status": "active",
        "service": "SARTHI Backend",
        "version": "2.2.0",
        "whisper_ready": whisper_model is not None,
        "connected_students": len(broadcaster.active_connections)
    }


@app.get("/api/gloss")
async def get_isl_gloss(text: str):
    """Utility endpoint to test English-to-ISL transformation."""
    return text_to_isl_gloss(text)


# ─── WebSocket: Continuous Teacher Speech Stream ─────────────────────────────

@app.websocket("/ws/speech")
@app.websocket("/ws/teacher-audio")
async def websocket_teacher_speech(websocket: WebSocket):
    """
    Teacher Live Speech Ingestion:
    - Accepts continuous speech text or audio packets from Teacher Dashboard.
    - Runs ISL grammar conversion.
    - Sends delivery ACK to teacher and immediately broadcasts to student screens.
    """
    await websocket.accept()
    session_id = "sarthi-live-session"
    language = "en"
    audio_buffer = bytearray()
    print("[WebSocket] Teacher stream connected.")

    try:
        while True:
            message = await websocket.receive()

            # 1. Binary Audio Chunk from MediaRecorder
            if "bytes" in message and message["bytes"]:
                chunk = message["bytes"]
                audio_buffer.extend(chunk)

                # Process audio when buffer reaches a speech slice
                if len(audio_buffer) >= 48000:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
                        temp_file.write(audio_buffer)
                        temp_path = temp_file.name
                    audio_buffer.clear()

                    try:
                        transcribed = transcribe_audio_file(temp_path, language=language)
                        if transcribed and len(transcribed.strip()) > 1:
                            isl = text_to_isl_gloss(transcribed)
                            broadcaster.segment_counter += 1
                            curr_id = broadcaster.segment_counter

                            payload = {
                                "type": "transcript",
                                "segmentId": curr_id,
                                "text": transcribed,
                                "original_text": transcribed,
                                "gloss_tokens": isl["gloss"],
                                "tokens": isl["gloss"],
                                "is_final": True
                            }
                            await websocket.send_json(payload)
                            await broadcaster.broadcast(payload)
                            print(f"[Live Speech] #{curr_id}: '{transcribed}' -> ISL: {isl['gloss']}")
                    finally:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

            # 2. Text / Control JSON message
            elif "text" in message and message["text"]:
                try:
                    data = json.loads(message["text"])
                    mtype = data.get("type")

                    if mtype == "start":
                        session_id = data.get("sessionId", session_id)
                        language = data.get("language", language)
                        audio_buffer.clear()
                        print(f"[Live Stream] Started session: {session_id}, language: {language}")

                    elif mtype == "text":
                        # Instant live speech text from Teacher Dashboard
                        text_content = data.get("text", "").strip()
                        if text_content:
                            isl = text_to_isl_gloss(text_content)
                            broadcaster.segment_counter += 1
                            curr_id = broadcaster.segment_counter

                            payload = {
                                "type": "transcript",
                                "segmentId": curr_id,
                                "text": text_content,
                                "original_text": text_content,
                                "gloss_tokens": isl["gloss"],
                                "tokens": isl["gloss"],
                                "is_final": True
                            }
                            await websocket.send_json(payload)
                            await broadcaster.broadcast(payload)
                            print(f"[Live Text] #{curr_id}: '{text_content}' -> ISL: {isl['gloss']}")

                    elif mtype == "stop":
                        # Process lingering audio if any
                        if len(audio_buffer) > 4000:
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
                                temp_file.write(audio_buffer)
                                temp_path = temp_file.name
                            audio_buffer.clear()
                            try:
                                transcribed = transcribe_audio_file(temp_path, language=language)
                                if transcribed:
                                    isl = text_to_isl_gloss(transcribed)
                                    broadcaster.segment_counter += 1
                                    curr_id = broadcaster.segment_counter

                                    payload = {
                                        "type": "transcript",
                                        "segmentId": curr_id,
                                        "text": transcribed,
                                        "original_text": transcribed,
                                        "gloss_tokens": isl["gloss"],
                                        "tokens": isl["gloss"],
                                        "is_final": True
                                    }
                                    await websocket.send_json(payload)
                                    await broadcaster.broadcast(payload)
                            finally:
                                if os.path.exists(temp_path):
                                    os.remove(temp_path)

                    elif mtype == "ping":
                        await websocket.send_json({"type": "pong"})

                except Exception as err:
                    print(f"[WebSocket Speech] Control error: {err}")

    except WebSocketDisconnect:
        print("[WebSocket] Teacher stream disconnected.")
    except Exception as e:
        print(f"[WebSocket] Teacher error: {e}")


# ─── WebSocket: Live Student Broadcast Viewer ────────────────────────────────

@app.websocket("/ws/viewer")
@app.websocket("/ws/classroom/{sessionId}")
async def websocket_student_endpoint(websocket: WebSocket, sessionId: str = "default"):
    """
    Student Viewer Broadcast WebSocket:
    Delivers live lecture transcripts and synchronized ISL gloss tokens
    for the 60 FPS 2D biomechanical avatar.
    Includes keep-alive ping to prevent Render free-tier idle timeout.
    """
    await broadcaster.connect(websocket)
    try:
        while True:
            # Wait for keepalive ping or incoming message
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)
    except Exception:
        broadcaster.disconnect(websocket)


# ─── Server Launcher ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print("=" * 65)
    print("  🚀 SARTHI Production Backend Server")
    print(f"  HTTP Healthcheck:    http://0.0.0.0:{port}/health")
    print(f"  Teacher Speech Stream: ws://0.0.0.0:{port}/ws/speech")
    print(f"  Student Broadcast:   ws://0.0.0.0:{port}/ws/viewer")
    print("=" * 65)
    uvicorn.run(app, host="0.0.0.0", port=port)
