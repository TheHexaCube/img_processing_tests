import os
import dearpygui.dearpygui as dpg
import numpy as np

from base.img_generator import ImageGenerator
from base.img_processor import ImageProcessor


class MainWindow:
    def __init__(self): 

        self.img_generator = ImageGenerator()
        self.img_processor = ImageProcessor()
        
        dpg.create_context()
        dpg.create_viewport(title="Main Window", width=750, height=900)
        dpg.setup_dearpygui()

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
            dpg.set_item_label(self.start_button, "Start processing")
        else:
            self.img_generator.start()
            dpg.set_item_label(self.start_button, "Stop processing")

    def show(self):
        dpg.show_viewport()

        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()

        self.cleanup()
        dpg.destroy_context()

    def cleanup(self):
        pass