import os
import dearpygui.dearpygui as dpg
import numpy as np

from base.img_generator import ImageGenerator
from base.img_processor import ImageProcessor


class MainWindow:
    def __init__(self): 

        self.img_generator = ImageGenerator(framerate=30, resolution=(1000, 1000))
        self.img_processor = ImageProcessor()

        self.img_generator.register_callback(self.img_processor.set_raw_frame)
        self.img_processor.register_callback(self.frame_received_callback)

        
        
        dpg.create_context()
        dpg.create_viewport(title="Main Window", width=750, height=900)
        dpg.setup_dearpygui()

        with dpg.handler_registry():
            dpg.add_key_press_handler(callback=self.key_press_callback)

        with dpg.texture_registry():
            self.img_texture = dpg.add_raw_texture(tag='img_texture', width=1000, height=1000, default_value=np.zeros((1000, 1000, 3), dtype=np.float32), format=dpg.mvFormat_Float_rgb)

        with dpg.window(label="Base Test", tag="MainWindow"):

            self.start_button = dpg.add_button(label="Start processing", width=150, height=30, callback=self.button_callback)

            with dpg.group():
                with dpg.plot(label="Execution Time Plot", height=250, width=650, equal_aspects=True):
                    dpg.add_plot_axis(dpg.mvXAxis, label="X")
                    dpg.add_plot_axis(dpg.mvYAxis, label="Y", tag="execution_time_y_axis")

                with dpg.plot(label="Image Plot", height=650, width=650, equal_aspects=True):
                    dpg.add_plot_axis(dpg.mvXAxis, label="X")
                    dpg.add_plot_axis(dpg.mvYAxis, label="Time (ms)", tag="img_y_axis")

                    dpg.add_image_series('img_texture', bounds_min=(0, 0), bounds_max=(1000, 1000), parent="img_y_axis", tag="img_series")

                

        dpg.set_primary_window("MainWindow", True)

    def button_callback(self):
        if self.img_generator.is_running():
            self.img_generator.stop()
            self.img_processor.stop()
            dpg.set_item_label(self.start_button, "Start processing")
        else:
            self.img_generator.start()
            self.img_processor.start()
            dpg.set_item_label(self.start_button, "Stop processing")

    def show(self):
        dpg.show_viewport()

        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()

        self.cleanup()
        dpg.destroy_context()

    def frame_received_callback(self, frame):
        if frame is not None:
            dpg.set_value(self.img_texture, frame)
            print(f"Frame received: {frame.shape}")

    def key_press_callback(self, sender, app_data):
        if (dpg.is_key_down(dpg.mvKey_LControl) and dpg.is_key_down(dpg.mvKey_M)):
            dpg.show_metrics()
        

    def cleanup(self):
        pass