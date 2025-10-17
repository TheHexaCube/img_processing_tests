import numpy as np
import cv2
import time
import threading
from collections import deque

# Handle profiling decorator if available
try:
    from line_profiler import profile
except ImportError:
    def profile(func):
        return func


''' 
This module will serve as a 'virtual camera' that creates frames at a set framerate and resolution.
''' 

class ImageGenerator:
    def __init__(self, framerate=60, resolution=(1000, 1000)):
        
        self.framerate = framerate

        self.width = resolution[0]
        self.height = resolution[1]

        self.running = False
        self.thread = None

        self.frame = None

        self.frame_count = 0

        self.last_execution_time = 0
        self.avg_execution_time = 0
        
        # Thread-safe storage for execution times (keep last 100 measurements)
        self.execution_times = deque(maxlen=500)  # Store (start_time, end_time) tuples
        self.execution_times_lock = threading.Lock()
        
        # FPS tracking
        self.frame_timestamps = deque(maxlen=500)  # Keep timestamps for FPS calculation
        self.fps_timestamps_lock = threading.Lock()
        

        self.frame_done_callback = None

        self.generator = np.random.randint(0, 4096, (self.height, self.width, 3), dtype=np.uint16)
        self.bayer_pattern_1 = np.empty((self.height, self.width), dtype=np.uint16)
        self.bayer_pattern_1[0::2, 0::2] = self.generator[0::2, 0::2, 0]  # R
        self.bayer_pattern_1[0::2, 1::2] = self.generator[0::2, 1::2, 1]  # G
        self.bayer_pattern_1[1::2, 0::2] = self.generator[1::2, 0::2, 1]  # G
        self.bayer_pattern_1[1::2, 1::2] = self.generator[1::2, 1::2, 2]  # B

        self.generator = np.random.randint(0, 4096, (self.height, self.width, 3), dtype=np.uint16)
        self.bayer_pattern_2 = np.empty((self.height, self.width), dtype=np.uint16)
        self.bayer_pattern_2[0::2, 0::2] = self.generator[0::2, 0::2, 1]  # G
        self.bayer_pattern_2[0::2, 1::2] = self.generator[0::2, 1::2, 2]  # B
        self.bayer_pattern_2[1::2, 0::2] = self.generator[1::2, 0::2, 2]  # B
        self.bayer_pattern_2[1::2, 1::2] = self.generator[1::2, 1::2, 0]  # R

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.generate_frames)
        self.thread.start()
        print(f"Image generator started. Resolution: {self.width}x{self.height}")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        self.thread = None
        self.frame = None
        print(f"Image generator stopped. Total frames generated: {self.frame_count}")

    @profile
    def generate_frames(self):
        frame_interval = 1.0 / self.framerate  # Time between frames in seconds
        last_frame_time = time.perf_counter()
        
        while self.running:
            frame_start_time = time.perf_counter()

            source_frame = self.generator

           

            frame_end_time = time.perf_counter()
            
            # Store execution time thread-safely as a tuple
            with self.execution_times_lock:
                self.execution_times.append((frame_start_time, frame_end_time))
                self.last_execution_time = frame_end_time - frame_start_time
            
            #print(f"Frame generation execution time: {self.last_execution_time:.6f} seconds")
            self.frame_count += 1
            
            # Store timestamp for FPS calculation
            current_time = time.time()
            with self.fps_timestamps_lock:
                self.frame_timestamps.append(current_time)

            if self.frame_done_callback:
                # randomly choose between bayer_pattern_1 and bayer_pattern_2
                if np.random.rand() < 0.5:
                    bayer_pattern = self.bayer_pattern_1
                else:
                    bayer_pattern = self.bayer_pattern_2
                self.frame_done_callback(bayer_pattern)
            
            # Frame rate control - wait until it's time for the next frame
            elapsed_time = frame_end_time - last_frame_time
            sleep_time = frame_interval - (time.perf_counter() - frame_start_time)
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            last_frame_time = time.perf_counter()

    def get_frame(self):
        return self.frame

    def is_running(self):
        return self.running

    def calculate_avg_execution_time(self):
        pass

    def register_callback(self, callback):
        self.frame_done_callback = callback
    
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
        """Calculate FPS based on frames generated in the last 1 second (thread-safe)"""
        current_time = time.time()
        with self.fps_timestamps_lock:
            # Count frames in the last 1 second
            one_second_ago = current_time - 1.0
            recent_frames = [ts for ts in self.frame_timestamps if ts >= one_second_ago]
            return len(recent_frames)
    
    def get_target_fps(self):
        """Get the target framerate"""
        return self.framerate
    
    def reset_statistics(self):
        """Reset all performance statistics (thread-safe)"""
        with self.execution_times_lock:
            self.execution_times.clear()
        
        with self.fps_timestamps_lock:
            self.frame_timestamps.clear()
        
        self.last_execution_time = 0
        print("Image generator statistics reset")


