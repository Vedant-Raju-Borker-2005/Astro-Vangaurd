import cv2
import mediapipe as mp
import numpy as np
import threading
import time
from typing import Optional
from PIL import Image as PILImage
import arcade

mp_hands   = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_styles  = mp.solutions.drawing_styles

class GestureController:
    """
    Self-contained gesture recognition system.
    Runs MediaPipe Hands in a background thread, exports:
      - gesture_state: "MOVE", "FIRE", "STOP", "IDLE"
      - finger_angle:  radians (direction from index finger)
      - camera_texture: arcade.Texture for in-game preview
    No cv2.imshow() — everything renders inside the game window.
    """

    # Preview dimensions
    PREVIEW_W = 200
    PREVIEW_H = 150

    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Shared state (protected by _lock)
        self._instance_id = str(int(time.time() * 1000))[-6:] # Unique ID for this session
        self._gesture_state = "IDLE"
        self._camera_frame_rgb: Optional[np.ndarray] = None
        self._texture_counter = 0
        self._stop_event = threading.Event()
        self._camera_texture = None

    # ── public properties (thread-safe reads) ───────────
    @property
    def gesture_state(self) -> str:
        with self._lock:
            return self._gesture_state

    @property
    def camera_frame_rgb(self) -> Optional[np.ndarray]:
        with self._lock:
            return self._camera_frame_rgb.copy() if self._camera_frame_rgb is not None else None

    # ── lifecycle ───────────────────────────────────────
    def start(self):
        if self._running:
            return
        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        # Wipe all stale state so nothing leaks into a new session
        with self._lock:
            self._gesture_state = "IDLE"
            self._camera_frame_rgb = None
            self._camera_texture = None

    @property
    def is_running(self) -> bool:
        return self._running

    # ── arcade texture (call from main/draw thread) ─────
    def get_camera_texture(self) -> Optional[arcade.Texture]:
        """Convert latest camera frame to an arcade.Texture. Call from draw thread."""
        frame = self.camera_frame_rgb
        if frame is None:
            return None
        try:
            # Resize for preview
            h, w = frame.shape[:2]
            preview = cv2.resize(frame, (self.PREVIEW_W, self.PREVIEW_H),
                                 interpolation=cv2.INTER_AREA)
            pil_img = PILImage.fromarray(preview)
            self._texture_counter += 1
            tex_name = f"gesture_cam_{self._instance_id}_{self._texture_counter}"
            texture = arcade.Texture(tex_name, image=pil_img)
            return texture
        except Exception:
            return None

    # ── worker thread ───────────────────────────────────
    def _worker(self):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ GestureController: Could not open webcam.")
            self._running = False
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        with mp_hands.Hands(
            static_image_mode=False, max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.6
        ) as hands:
            while self._running and not self._stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    time.sleep(0.03)
                    continue

                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = hands.process(rgb)

                gesture = "IDLE"
                if result.multi_hand_landmarks:
                    hand_lm = result.multi_hand_landmarks[0]
                    hand_info = result.multi_handedness[0]
                    lm = hand_lm.landmark

                    mp_drawing.draw_landmarks(
                        frame, hand_lm, mp_hands.HAND_CONNECTIONS,
                        mp_styles.get_default_hand_landmarks_style(),
                        mp_styles.get_default_hand_connections_style())

                    handedness = hand_info.classification[0].label \
                        if hasattr(hand_info.classification[0], 'label') else "Right"

                    finger_states = self._get_finger_states(lm, handedness)
                    thumb, index, middle, ring, pinky = finger_states

                    wrist = lm[0]
                    index_mcp = lm[5]
                    pinky_mcp = lm[17]
                    v1x = index_mcp.x - wrist.x
                    v1y = index_mcp.y - wrist.y
                    v2x = pinky_mcp.x - wrist.x
                    v2y = pinky_mcp.y - wrist.y
                    cross_z = v1x * v2y - v1y * v2x
                    if handedness == "Right":
                        palm_facing = cross_z > 0
                    else:
                        palm_facing = cross_z < 0

                    if index and middle and ring:
                        if palm_facing:
                            gesture = "TURN_RIGHT"
                        else:
                            gesture = "TURN_LEFT"
                    elif index and not middle and ring and pinky:
                        gesture = "POWER_WEAPON"
                    elif index and middle and not ring and not pinky:
                        gesture = "FIRE"
                    elif index and not middle and not ring and not pinky:
                        gesture = "FORWARD"
                    elif not index and not middle and not ring and not pinky:
                        gesture = "BACKWARD"
                    else:
                        gesture = "IDLE"

                if not self._stop_event.is_set():
                    preview_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    with self._lock:
                        self._gesture_state = gesture
                        self._camera_frame_rgb = preview_rgb

                time.sleep(0.033)

        cap.release()
        with self._lock:
            self._gesture_state = "IDLE"
            self._camera_frame_rgb = None
        self._running = False

    @staticmethod
    def _get_finger_states(lm, handedness_label: str):
        tips = [4, 8, 12, 16, 20]
        pips = [3, 6, 10, 14, 18]
        states = []
        if handedness_label == "Right":
            states.append(lm[tips[0]].x < lm[pips[0]].x)
        else:
            states.append(lm[tips[0]].x > lm[pips[0]].x)
        for i in range(1, 5):
            states.append(lm[tips[i]].y < lm[pips[i]].y)
        return states
