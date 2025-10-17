import cv2
import numpy as np
import time
import threading
from collections import deque

# Handle profiling decorator if available
try:
    from line_profiler import profile
except ImportError:
    def profile(func):
        return func

class ImageProcessor:
    def __init__(self):
        self.thread = None
        self.running = False

        self._raw_frame = None
        self._processed_frame = None

        self.frame_done_callback = None

        self.scale_factor = 1.0 / 4095.0
        
        # Thread-safe storage for execution times (keep last 100 measurements)
        self.execution_times = deque(maxlen=500)  # Store (start_time, end_time) tuples
        self.execution_times_lock = threading.Lock()
        self.last_execution_time = 0
        
        # FPS tracking
        self.frame_timestamps = deque(maxlen=500)  # Keep timestamps for FPS calculation
        self.fps_timestamps_lock = threading.Lock()
        
        # Frame drop tracking - processor drops frames when new ones arrive before processing is done
        self.frames_dropped = 0
        self.frames_dropped_lock = threading.Lock()

    def start(self):
        print("Image processor started")
        self.running = True
        self.thread = threading.Thread(target=self.process_frames)
        self.thread.start()
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        self.thread = None
        print("Image processor stopped")
    
    @profile
    def process_frames(self):
        while self.running:
            if self._raw_frame is not None:
                start_time = time.perf_counter()
                
                rgb = cv2.cvtColor(self._raw_frame, cv2.COLOR_BayerRG2RGB)
                rgb = cv2.normalize(rgb, None, alpha=0.0, beta=1.0, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
                
                end_time = time.perf_counter()
                
                # Store execution time thread-safely as a tuple
                with self.execution_times_lock:
                    self.execution_times.append((start_time, end_time))
                    self.last_execution_time = end_time - start_time
                
                #print(f"Image processing execution time: {self.last_execution_time:.6f} seconds")
                
                # Store timestamp for FPS calculation
                current_time = time.time()
                with self.fps_timestamps_lock:
                    self.frame_timestamps.append(current_time)

                if self.frame_done_callback:
                    self.frame_done_callback(rgb.ravel())
                
                # Clear the frame after processing to avoid reprocessing the same frame
                self._raw_frame = None
            
    
    def register_callback(self, callback):
        self.frame_done_callback = callback
    
    def is_running(self):
        return self.running

    def set_raw_frame(self, raw_frame):        
        # If there's already a frame waiting to be processed, we're dropping frames
        if self._raw_frame is not None:
            with self.frames_dropped_lock:
                self.frames_dropped += 1
        
        self._raw_frame = raw_frame
    
    def get_execution_times(self):
        """Get a copy of execution times for plotting (thread-safe)"""
        with self.execution_times_lock:
            if not self.execution_times:
                return [], []
            start_times, end_times = zip(*self.execution_times)
            return list(start_times), list(end_times)
    
    def get_last_execution_time(self):
        """Get the last execution time (thread-safe)"""
        with self.execution_times_lock:
            return self.last_execution_time
    
    def get_fps(self):
        """Calculate FPS based on frames processed in the last 1 second (thread-safe)"""
        current_time = time.time()
        with self.fps_timestamps_lock:
            # Count frames in the last 1 second
            one_second_ago = current_time - 1.0
            recent_frames = [ts for ts in self.frame_timestamps if ts >= one_second_ago]
            return len(recent_frames)
    
    def get_frames_dropped(self):
        """Get the number of frames dropped by the processor (thread-safe)"""
        with self.frames_dropped_lock:
            return self.frames_dropped
    
    def reset_statistics(self):
        """Reset all performance statistics (thread-safe)"""
        with self.execution_times_lock:
            self.execution_times.clear()
        
        with self.fps_timestamps_lock:
            self.frame_timestamps.clear()
        
        with self.frames_dropped_lock:
            self.frames_dropped = 0
        
        self.last_execution_time = 0
        print("Image processor statistics reset")
    