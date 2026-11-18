import queue
import threading
import sounddevice as sd
import logging
from ..core.config import config

logger = logging.getLogger(__name__)


def probe_best_microphone():
    """Detect candidate microphones and return the most suitable active input device."""
    try:
        devices = sd.query_devices()
        default_dev = sd.default.device[0] if sd.default.device else None

        # Priority 1: Realtek Audio Array (built-in high-gain array)
        realtek_idx = None
        for i, d in enumerate(devices):
            if d.get("max_input_channels", 0) > 0:
                name_lower = d.get("name", "").lower()
                if "realtek" in name_lower and "array" in name_lower:
                    realtek_idx = i
                    break

        chosen = realtek_idx if realtek_idx is not None else default_dev
        if chosen is not None and chosen < len(devices):
            dev_name = devices[chosen]["name"]
        else:
            dev_name = "Default"
        return chosen, dev_name
    except Exception as e:
        logger.warning(f"Error probing microphones: {e}")
        return None, "Default"


class Microphone:
    def __init__(self):
        self._queues = set()
        self._queues_lock = threading.Lock()
        self.stream = None
        self.device_index = None
        self.device_name = "Default"

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

        # Automatic fallback to best available microphone if not specified
        if device_index is None:
            device_index = getattr(config, "MIC_DEVICE_INDEX", None)

        if device_index is None:
            device_index, dev_name = probe_best_microphone()
        else:
            try:
                dev_name = sd.query_devices(device_index)["name"]
            except Exception:
                dev_name = f"Device {device_index}"

        self.device_index = device_index
        self.device_name = dev_name

        self.stream = sd.InputStream(
            device=device_index,
            samplerate=config.SAMPLERATE,
            channels=config.CHANNELS,
            blocksize=config.BLOCK_SIZE,
            callback=self._callback
        )
        self.stream.start()
        logger.info(f"Microphone stream started (Device [{self.device_index}]: {self.device_name}).")

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
