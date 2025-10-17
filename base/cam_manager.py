import os
import sys
#sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pypylon import pylon
import threading
import numpy as np
#from utils.logger import Logger, set_global_log_level_by_name
import cv2
import time
from line_profiler import profile
#from numba import jit, njit




def process_frame_gpu(raw_frame, pixel_format):
    """
    GPU-accelerated frame processing using CuPy.
    Only used in _callback_thread.
    """
    


    # Determine bit depth from pixel format
    max_value = 255.0 if "8" in pixel_format else 4095.0
    
    if len(raw_frame.shape) == 2:  # Raw Bayer data      
        height, width = raw_frame.shape
        
        # demosaic via opencv debayering
        result = cv2.cvtColor(raw_frame, cv2.COLOR_BayerRG2RGB)
        cv2.normalize(result, result, 0, 1, cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        return result.flatten()

      
''' CamManager class 
    This class is used to manage/connect to Basler Cameras
''' 
class CamManager:
    def __init__(self):
        self.tl_factory = pylon.TlFactory.GetInstance()
        self.devices = self.tl_factory.EnumerateDevices()
        self.current_cam = None
        self._capture_thread = None
        self._stop_event = threading.Event()
        self._frame_count = 0

        self._raw_frame = None
        self._processed_frame = None

        self._width = None
        self._height = None

        self._frame_lock = threading.Lock()  # Thread safety for frame access
        self._is_new_frame = False
        self._frame_ready_event = threading.Event()
        self._norm_buf = None
        
        


    def list_cameras(self):
        # return a list of available cameras (index, model_name, serial_no)
        self.devices = self.tl_factory.EnumerateDevices()
        
        return [(index, device.GetModelName(), device.GetSerialNumber()) for index, device in enumerate(self.devices)]

    def connect(self, index: int):
        if self.list_cameras() is None:            
            raise ValueError("No cameras found")
        if index < 0 or index >= len(self.devices):            
            raise ValueError(f"Invalid camera index: {index}")


        if self.current_cam and self.current_cam.IsOpen():
            self.current_cam.Close()

        self.current_cam = pylon.InstantCamera(self.tl_factory.CreateDevice(self.devices[index]))
        self.current_cam.Open()
        
        

    def disconnect(self):
        '''
        Disconnect from the camera
        '''
        # Stop capture first if it's running
        if self.is_capturing():
            self.stop_capture()
        
        # Clear all callbacks
        #self.clear_all_callbacks()
        
        # Close camera
        if self.current_cam and self.current_cam.IsOpen():
            self.current_cam.Close()
        self.current_cam = None
        

    def start_capture(self):
        if not self.current_cam or not self.current_cam.IsOpen():
            raise RuntimeError("Camera is not connected")
        if self.current_cam.IsGrabbing():
            raise RuntimeError("Camera is already capturing")

        self.set_exposure_time(100)
        self.set_gain(0)
        self.current_cam.PixelFormat.Value = "BayerRG12"
       
        self.current_cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        
        self._stop_event.clear()
        self._frame_count = 0
        self._gpu_failure_count = 0  # Track GPU failures
        self._max_gpu_failures = 3  # Switch to CPU after 3 failures
        self._capture_thread = threading.Thread(target=self._callback_thread)
        self._capture_thread.start()
        

    def stop_capture(self):
        '''
        Stop capturing
        '''
        if self._capture_thread and self._capture_thread.is_alive():
            self._stop_event.set()
            self._frame_ready_event.set()  # Wake up any waiting threads
            self._capture_thread.join()
            self._capture_thread = None
            

    def _callback_thread(self):
        '''
        Thread to handle the callback from the camera
        Measures the time between loops and logs it in ms and FPS.
        '''
        prev_time = time.time()
        while not self._stop_event.is_set():

            grabResult = self.current_cam.RetrieveResult(5000)
            if grabResult.GrabSucceeded():
                # Thread-safe frame processing
                with self._frame_lock:
                    self._raw_frame = grabResult.GetArray()
                    
                    # Use GPU acceleration if available, otherwise fallback to CPU
                    
                    
                    self._processed_frame = self.process_frame(self._raw_frame)

                
                    self._is_new_frame = True

                self._frame_ready_event.set()
                self._frame_count += 1

                # Measure and log timing
                curr_time = time.time()
                loop_time = curr_time - prev_time
                prev_time = curr_time
                ms = loop_time * 1000 if loop_time > 0 else 0.0
                fps = 1.0 / loop_time if loop_time > 0 else 0.0

                
                
            else:
                
                break

            grabResult.Release()
    
    @profile
    def process_frame(self, raw_frame):
        '''
        Process the raw frame to be used in the GUI
        Process: (1) Demosaic from BayerRG to RGB
                (2) Normalize to 0-1 range
                (3) Return the processed frame as a flattened array
        '''
        self.scale = 1.0 / 4095.0         
  
        rgb = cv2.cvtColor(raw_frame, cv2.COLOR_BayerRG2RGB)
        rgb = cv2.normalize(rgb, None, alpha=0, beta=1.0, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        return rgb.ravel()
       

    # ---- camera settings ----

    def set_exposure_time(self, exposure_time: int):
        '''
        Set the exposure time of the camera
        '''
        self.current_cam.ExposureTime.SetValue(exposure_time)
        
    def get_exposure_time(self):
        '''
        Get the exposure time of the camera
        '''
        return self.current_cam.ExposureTime.GetValue()

    def set_gain(self, gain: int):
        '''
        Set the gain of the camera
        '''
        self.current_cam.Gain.SetValue(gain)
        
        
    def get_gain(self):
        '''
        Get the gain of the camera
        '''
        return self.current_cam.Gain.GetValue()
        
    # ---- camera/state info ---- 
    def is_connected(self):
        '''
        Check if the camera is connected
        '''
        return self.current_cam is not None and self.current_cam.IsOpen()
    
    def is_capturing(self):
        '''
        Check if the camera is capturing
        '''
        return self._capture_thread is not None and self._capture_thread.is_alive()
    
    def get_raw_frame(self):
        '''
        Get the raw frame from the camera (thread-safe)
        '''
        with self._frame_lock:            
                if self._raw_frame is not None:
                    self._is_new_frame = False
                    return self._raw_frame.copy()
                else:
                    return None
        
    def get_processed_frame(self):
        '''
        Get the processed frame from the camera (thread-safe)
        '''
        with self._frame_lock:            
            if self._processed_frame is not None:
                self._is_new_frame = False
                self._frame_ready_event.clear()  # Reset for next frame
                return self._processed_frame.copy()
            else:
                return None
  
    
    def get_resolution(self):
        '''
        Get the resolution of the camera
        '''
        if self.current_cam.IsOpen():
            self._width = self.current_cam.Width.GetValue()
            self._height = self.current_cam.Height.GetValue()
            return self._width, self._height
        else:
            raise RuntimeError("Camera is not connected")
        
    
    def __del__(self):
        self.disconnect()
