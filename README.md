## img_processing_tests — Baseline for Bayer frame processing

This project is a small, single-machine baseline to test and optimize a Bayer-frame processing pipeline. It generates synthetic Bayer frames at a target framerate, processes them into RGB, and visualizes both the images and the performance characteristics in real time.

### Goals
- Establish a reproducible baseline for frame generation and processing.
- Measure and visualize timing (execution time per frame, FPS, dropped frames).
- Provide a feedback loop for optimizing the processing stage.


## High-level architecture

- `base/img_generator.py` — Generates synthetic frames at a target FPS and resolution. Emits Bayer-pattern frames via a callback.
- `base/img_processor.py` — Receives Bayer frames, converts to RGB (OpenCV demosaic), normalizes, and emits the processed image via a callback.
- `base/GUI.py` — Dear PyGui UI. Displays the processed image, live performance metrics, and plots.
- `main.py` — Entrypoint that creates and shows the main window.

Key interactions:
- `ImageGenerator.register_callback(...)` connects generator → processor (`ImageProcessor.set_raw_frame`).
- `ImageProcessor.register_callback(...)` connects processor → GUI texture upload (`MainWindow.frame_received_callback`).


## Data flow
1. Generator builds a synthetic RGB array and converts it to a BayerRG-pattern single-channel image:
   - R at indices `(0::2, 0::2)`
   - G at indices `(0::2, 1::2)` and `(1::2, 0::2)`
   - B at indices `(1::2, 1::2)`
2. The Bayer image is pushed to the processor via `set_raw_frame`.
3. The processor:
   - Records start time (perf_counter)
   - Converts Bayer → RGB with `cv2.COLOR_BayerRG2RGB`
   - Normalizes to float32 in [0, 1]
   - Records end time (perf_counter)
   - Emits the `rgb.ravel()` data to the GUI callback
4. The GUI uploads the flattened RGB float texture to a Dear PyGui raw texture and displays it.


## Threading model
- Generator runs on its own thread; target framerate is enforced with sleep (`1 / framerate`).
- Processor runs on its own thread; processes the latest available frame.
- GUI runs Dear PyGui’s main loop; a background thread updates UI/plots.

Frame drops: If a new frame arrives while the previous one hasn’t been consumed by the processor, `ImageProcessor.set_raw_frame` overwrites the pending frame and increments `frames_dropped`. This is intentional to keep latency low and measure realistic processing throughput.


## Performance metrics and plots

Tracked metrics:
- Generator FPS and Processor FPS (rolling, last ~1s window)
- Processor dropped frames count
- Last processor execution time (seconds)

Timing collection:
- Both generator and processor store synchronized `(start_time, end_time)` tuples in a thread-safe `deque`.
- The GUI computes per-frame execution times as `end_time - start_time`.

Plots:
- X-axis: Relative time (seconds since a stable reference taken at first data arrival)
- Y-axis: Execution time (milliseconds)
- Two line series: "Frame Generation" and "Frame Processing"
- A 10-frame moving average is applied in the GUI for smoother curves.

Why generator and processor series can differ in length:
- The generator emits one timing per generated frame.
- The processor may drop frames; therefore, it will often have fewer timing samples over the same wall-clock period.


## Configuration and tuning

- Resolution and framerate are configured in `base/GUI.py`:
  - `FRAME_RESOLUTION = (width, height)`
  - `ImageGenerator(framerate=..., resolution=FRAME_RESOLUTION)`
- The image texture and image plot bounds are tied to `FRAME_RESOLUTION`.
- Smoothing window (moving average) is configured via `self.averaging_window` in `MainWindow` (default 10).

Tips for optimization experiments:
- Replace or augment the demosaic/processing in `ImageProcessor.process_frames`.
- Compare execution time and FPS before/after changes.
- Watch dropped frames to see if throughput improved.
- Keep test inputs stable (same resolution/FPS) when comparing results.


## Running the app

### Requirements
- Python 3.9+
- Packages:
  - `numpy`
  - `opencv-python`
  - `dearpygui`
  - `line_profiler` (optional; the code falls back gracefully if missing)

Install dependencies:

```bash
pip install numpy opencv-python dearpygui line_profiler
```

### Start

From the project root (`img_processing_tests`):

```bash
python main.py
```


## Using the UI
- Click "Start processing" to start/stop generator and processor threads.
- "Reset Stats" clears FPS, counters, plots, and resets the plotting reference time.
- Plots:
  - Execution Time Plot — two averaged lines (generator/processor) vs time.
  - Image Plot — current processed frame (float32 RGB texture).
- Press Ctrl+M to open Dear PyGui metrics.


## Baseline scope and extensibility
This repo is intended as a baseline for measuring the impact of processing optimizations on Bayer frames. You can:
- Swap in different demosaic algorithms (OpenCV alternatives, custom kernels, GPU paths, etc.).
- Add additional timing around stages (IO, pre/post-processing) and expose them to the plotter.
- Introduce a fixed time window or resampled common-grid plotting if you prefer equal point counts across series.


## Notes on timing stability
- We use `time.perf_counter()` for precise interval timing.
- A stable reference time is captured once for the plots to avoid axis jitter.
- All timing structures are protected by locks to avoid race conditions and index errors.


## Troubleshooting
- "List index out of range": Usually a sign of unsynchronized timing arrays; fixed by storing `(start, end)` tuples atomically.
- Flickering plots: Caused by a moving reference; fixed by stabilizing the reference time and applying moving averages.
- Processor samples < generator samples: Expected if the processor drops frames; monitor `Dropped` in the UI.


