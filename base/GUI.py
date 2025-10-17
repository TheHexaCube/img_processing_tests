import os
import dearpygui.dearpygui as dpg
import numpy as np
import threading
import time

from base.img_generator import ImageGenerator
from base.img_processor import ImageProcessor


FRAME_RESOLUTION = (2048, 1536)
FPS_GENERATOR = 100

class MainWindow:
    def __init__(self): 

        self.img_generator = ImageGenerator(framerate=FPS_GENERATOR, resolution=FRAME_RESOLUTION)
        self.img_processor = ImageProcessor()

        self.img_generator.register_callback(self.img_processor.set_raw_frame)
        self.img_processor.register_callback(self.frame_received_callback)
        
        # Plot update thread
        self.plot_update_thread = None
        self.plot_running = False
        self.reference_time = None  # Stable reference time for plotting
        
        # Averaging settings
        self.averaging_window = 20  # Number of frames to average over

        
        
        dpg.create_context()
        dpg.create_viewport(title="Main Window", width=750, height=900)
        dpg.setup_dearpygui()

        with dpg.handler_registry():
            dpg.add_key_press_handler(callback=self.key_press_callback)

        with dpg.texture_registry():
            self.img_texture = dpg.add_raw_texture(tag='img_texture', width=FRAME_RESOLUTION[0], height=FRAME_RESOLUTION[1], default_value=np.zeros((FRAME_RESOLUTION[0], FRAME_RESOLUTION[1], 3), dtype=np.float32), format=dpg.mvFormat_Float_rgb)

        with dpg.window(label="Base Test", tag="MainWindow"):

            with dpg.group(horizontal=True):
                self.start_button = dpg.add_button(label="Start processing", width=150, height=30, callback=self.button_callback)
                self.reset_button = dpg.add_button(label="Reset Stats", width=120, height=30, callback=self.reset_button_callback)

            # Performance metrics section
            with dpg.group():
                with dpg.group(horizontal=True):
                    dpg.add_text("Generator:")
                    dpg.add_text("Target: 120.0 FPS", tag="generator_target_text", color=(200, 200, 200))
                    dpg.add_text("Actual: ", tag="generator_actual_label")
                    dpg.add_text("0.0 FPS", tag="generator_fps_text", color=(0, 255, 255))  # Cyan color
                
                with dpg.group(horizontal=True):
                    dpg.add_text("Processor:")
                    dpg.add_text("Processing: ", tag="processor_label")
                    dpg.add_text("0.0 FPS", tag="processor_fps_text", color=(255, 165, 0))  # Orange color
                    dpg.add_text("Dropped: ", tag="processor_dropped_label")
                    dpg.add_text("0", tag="processor_dropped_text", color=(255, 100, 100))  # Red color
                    dpg.add_text("Last Exec: ", tag="processor_exec_label")
                    dpg.add_text("0.00 ms", tag="processor_exec_text", color=(100, 255, 100))  # Green color

            with dpg.group():
                with dpg.plot(label="Execution Time Plot", height=250, width=650):
                    dpg.add_plot_axis(dpg.mvXAxis, label="Time (seconds)", auto_fit=True)
                    dpg.add_plot_axis(dpg.mvYAxis, label="Execution Time (ms)", tag="execution_time_y_axis", auto_fit=True)
                    
                    # Add series for both generator and processor execution times
                    dpg.add_line_series([], [], label="Frame Generation", parent="execution_time_y_axis", tag="generator_series")
                    dpg.add_line_series([], [], label="Frame Processing", parent="execution_time_y_axis", tag="processor_series")

                with dpg.plot(label="Image Plot", height=650, width=650, equal_aspects=True):
                    dpg.add_plot_axis(dpg.mvXAxis, label="X")
                    dpg.add_plot_axis(dpg.mvYAxis, label="Time (ms)", tag="img_y_axis")

                    dpg.add_image_series('img_texture', bounds_min=(0, 0), bounds_max=(FRAME_RESOLUTION[0], FRAME_RESOLUTION[1]), parent="img_y_axis", tag="img_series")

                

        dpg.set_primary_window("MainWindow", True)

    def button_callback(self):
        if self.img_generator.is_running():
            self.img_generator.stop()
            self.img_processor.stop()
            self.stop_plot_updates()
            dpg.set_item_label(self.start_button, "Start processing")
        else:
            self.img_generator.start()
            self.img_processor.start()
            self.start_plot_updates()
            dpg.set_item_label(self.start_button, "Stop processing")
    
    def reset_button_callback(self):
        """Reset all performance statistics"""
        self.img_generator.reset_statistics()
        self.img_processor.reset_statistics()
        
        # Reset reference time for plotting
        self.reference_time = None
        
        # Clear the plots
        dpg.set_value("generator_series", [[], []])
        dpg.set_value("processor_series", [[], []])
        
        # Reset display values
        dpg.set_value("generator_fps_text", "0.0 FPS")
        dpg.set_value("processor_fps_text", "0.0 FPS")
        dpg.set_value("processor_dropped_text", "0")
        dpg.set_value("processor_exec_text", "0.00 ms")
        
        print("All statistics reset")

    def show(self):
        dpg.show_viewport()

        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()

        self.cleanup()
        dpg.destroy_context()

    def frame_received_callback(self, frame):
        if frame is not None:
            dpg.set_value(self.img_texture, frame)
            #print(f"Frame received: {frame.shape}")

    def key_press_callback(self, sender, app_data):
        if (dpg.is_key_down(dpg.mvKey_LControl) and dpg.is_key_down(dpg.mvKey_M)):
            dpg.show_metrics()
        

    def start_plot_updates(self):
        """Start the plot update thread"""
        self.plot_running = True
        self.plot_update_thread = threading.Thread(target=self.update_plots_thread)
        self.plot_update_thread.daemon = True
        self.plot_update_thread.start()
    
    def stop_plot_updates(self):
        """Stop the plot update thread"""
        self.plot_running = False
        if self.plot_update_thread:
            self.plot_update_thread.join()
        self.plot_update_thread = None
    
    def calculate_moving_average(self, timestamps, values, window_size):
        """Calculate moving average for timestamps and values"""
        if len(timestamps) < window_size:
            # Not enough data for averaging, return original data
            return timestamps, values
        
        # Calculate moving average
        averaged_timestamps = []
        averaged_values = []
        
        for i in range(window_size - 1, len(timestamps)):
            # Calculate average value over the window
            window_values = values[i - window_size + 1:i + 1]
            avg_value = sum(window_values) / window_size
            
            # Use the current timestamp
            averaged_timestamps.append(timestamps[i])
            averaged_values.append(avg_value)
        
        return averaged_timestamps, averaged_values
    
    def update_plots_thread(self):
        """Background thread to update plots with execution times"""
        while self.plot_running:
            try:
                gen_start_timestamps, gen_end_timestamps = self.img_generator.get_execution_times()
                proc_start_timestamps, proc_end_timestamps = self.img_processor.get_execution_times()

                # Only proceed if we have data
                if not gen_start_timestamps or not proc_start_timestamps:
                    time.sleep(0.01)
                    continue

                # Set reference time once at the beginning
                if self.reference_time is None:
                    all_start_timestamps = gen_start_timestamps + proc_start_timestamps
                    self.reference_time = min(all_start_timestamps)

                # Calculate execution times (delta times in seconds)
                gen_delta_times = [gen_end_timestamps[i] - gen_start_timestamps[i] for i in range(len(gen_start_timestamps))]
                proc_delta_times = [proc_end_timestamps[i] - proc_start_timestamps[i] for i in range(len(proc_start_timestamps))]
                
                # Convert absolute timestamps to relative time (seconds since reference)
                gen_relative_times = [(ts - self.reference_time) for ts in gen_end_timestamps]
                proc_relative_times = [(ts - self.reference_time) for ts in proc_end_timestamps]
                
                # Apply moving average to smooth the curves
                gen_avg_times, gen_avg_values = self.calculate_moving_average(
                    gen_relative_times, gen_delta_times, self.averaging_window
                )
                proc_avg_times, proc_avg_values = self.calculate_moving_average(
                    proc_relative_times, proc_delta_times, self.averaging_window
                )

                # Get FPS and stats
                generator_fps = self.img_generator.get_fps()
                processor_fps = self.img_processor.get_fps()
                generator_target_fps = self.img_generator.get_target_fps()
                processor_frames_dropped = self.img_processor.get_frames_dropped()
                processor_exec_time = self.img_processor.get_last_execution_time()

                # Update all UI displays
                dpg.set_value("generator_target_text", f"{generator_target_fps:.1f} FPS")
                dpg.set_value("generator_fps_text", f"{generator_fps:.1f} FPS")
                dpg.set_value("processor_fps_text", f"{processor_fps:.1f} FPS")
                dpg.set_value("processor_dropped_text", f"{processor_frames_dropped}")
                dpg.set_value("processor_exec_text", f"{processor_exec_time * 1000:.2f} ms")

                # Update the plots with averaged data (relative time on x-axis and execution time in ms on y-axis)
                dpg.set_value("generator_series", [gen_avg_times, [t * 1000 for t in gen_avg_values]])
                dpg.set_value("processor_series", [proc_avg_times, [t * 1000 for t in proc_avg_values]])

                # Update every 10ms for smooth real-time plotting
                time.sleep(0.01)

            except Exception as e:
                print(f"Error updating plots: {e}")
                time.sleep(0.1)

    def cleanup(self):
        self.stop_plot_updates()
        if self.img_generator.is_running():
            self.img_generator.stop()
        if self.img_processor.is_running():
            self.img_processor.stop()