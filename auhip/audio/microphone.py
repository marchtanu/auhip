import queue
import threading
import sounddevice as sd
import logging
from ..core.config import config

logger = logging.getLogger(__name__)

class Microphone:
    def __init__(self):
        self._queues = set()
        self._queues_lock = threading.Lock()
        self.stream = None

    def subscribe(self, maxsize=100):
        """Returns a new queue that will receive all audio chunks."""
        q = queue.Queue(maxsize=maxsize)
        with self._queues_lock:
            self._queues.add(q)
        return q

    def unsubscribe(self, q):
        """Removes a queue from the subscription list."""
        with self._queues_lock:
            self._queues.discard(q)

    def _callback(self, indata, frames, time, status):
        if status:
            logger.warning(f"Audio stream status: {status}")
        
        data = indata.copy()
        with self._queues_lock:
            queues_snapshot = list(self._queues)
        for q in queues_snapshot:
            try:
                q.put_nowait(data)
            except queue.Full:
                # Discard oldest to stay real-time if subscriber is lagging
                try:
                    q.get_nowait()
                    q.put_nowait(data)
                except (queue.Empty, queue.Full):
                    pass

    def start(self, device_index=None):
        if self.stream:
            self.stop()
            
        self.stream = sd.InputStream(
            device=device_index,
            samplerate=config.SAMPLERATE,
            channels=config.CHANNELS,
            blocksize=config.BLOCK_SIZE,
            callback=self._callback
        )
        self.stream.start()
        logger.info(f"Microphone stream started (Device: {device_index if device_index is not None else 'Default'}).")

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            logger.info("Microphone stream stopped.")

    def get_audio_chunk(self):
        """Legacy support for a single default queue if needed, but subscribe() is preferred."""
        # For backwards compatibility, we'll keep a default queue if nothing else is used
        if not hasattr(self, '_default_q'):
            self._default_q = self.subscribe()
        try:
            return self._default_q.get_nowait()
        except queue.Empty:
            return None
