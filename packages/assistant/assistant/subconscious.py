import threading
import queue
import time
import random
import logging
from typing import Optional, List, Callable
from .ai_client import AIClient

class SubconsciousBridge:
    """
    System 2 (Subconscious) for Bicameral Moshi.
    
    Monitors the conversation transcript and asynchronously queries a smarter model (Haiku)
    to inject facts, reasoning, or tool outputs into Moshi's stream.
    """
    def __init__(self, ai_client: AIClient, client_to_server_queue: Optional[queue.Queue] = None):
        self.ai_client = ai_client
        self.client_to_server = client_to_server_queue
        self.transcript_buffer = ""
        self.last_query_time = 0
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.logger = logging.getLogger("subconscious")
        
        # Phrases to smooth the insertion of external memories
        self.pivots = [
            " actually, I just realized ",
            " oh, and looking at the details, ",
            " wait, I recall that ",
            " correction, ",
            " specifically, "
        ]

    def start(self):
        """Start the subconscious monitoring loop."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True, name="SubconsciousMonitor")
        self.thread.start()
        self.logger.info("🧠 Subconscious Bridge started")

    def stop(self):
        """Stop the monitoring loop."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)

    def add_to_transcript(self, text: str):
        """Add text to the running transcript buffer."""
        self.transcript_buffer += text
        # Keep buffer manageable (last ~2000 chars)
        if len(self.transcript_buffer) > 2000:
            self.transcript_buffer = self.transcript_buffer[-2000:]

    def on_transcript_update(self, user_text: str, ai_text: str):
        """Called when a conversation turn is complete."""
        formatted = f"\nUser: {user_text}\nMoshi: {ai_text}\n"
        self.add_to_transcript(formatted)

    def _monitor_loop(self):
        """
        Constantly watches the transcript. If it sees a need for RAG/Reasoning,
        it queries Anthropic and queues the result.
        """
        while self.running:
            time.sleep(2.0) # Check every 2 seconds
            
            # Heuristic: Only query if enough time passed and buffer has content
            if time.time() - self.last_query_time > 5.0 and len(self.transcript_buffer) > 50:
                try:
                    self._query_brain()
                except Exception as e:
                    self.logger.error(f"Subconscious query failed: {e}")
                
                self.last_query_time = time.time()

    def _query_brain(self):
        """Query the smarter model (Haiku) to see if we should inject a thought."""
        # This prompt is critical. It tells Anthropic to be a "silent observer"
        system_prompt = (
            "You are the subconscious memory of an AI assistant. "
            "Read the current transcript. If the assistant is missing a fact, "
            "made a mistake, or needs to provide specific details, output the "
            "CORRECT sentence to say next. "
            "If the conversation is fine, output NOTHING (empty string). "
            "Keep your output short (1 sentence)."
        )
        
        # Use the AI client to generate a response
        # We use a separate method or model if possible, but for now reuse the main client
        # assuming it can handle concurrent requests or is fast enough.
        # Ideally we'd use a specific Haiku model here.
        
        try:
            # We need a way to force Haiku if the main client is using something else
            # For now, we rely on the AIClient's default or configured model.
            # TODO: Allow specifying model in generate()
            
            response = self.ai_client.generate_response(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"TRANSCRIPT:\n{self.transcript_buffer[-1000:]}"}
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            thought = response.strip()
            
            if thought and len(thought) > 5:
                self.logger.info(f"🧠 Subconscious thought: {thought}")
                self._inject_thought(thought)
                
        except Exception as e:
            self.logger.debug(f"Subconscious check skipped: {e}")

    def _inject_thought(self, thought: str):
        """Inject the thought into the voice server stream."""
        if not self.client_to_server:
            self.logger.warning("Cannot inject thought: No connection to voice server")
            return

        # Wrap it in a pivot
        pivot = random.choice(self.pivots)
        full_thought = f"{pivot}{thought}"
        
        self.logger.info(f"💉 Injecting: {full_thought}")
        
        # Send to voice server for tokenization and injection
        # The voice server handles tokenization to ensure compatibility with Moshi's tokenizer
        self.client_to_server.put(("inject", full_thought))
