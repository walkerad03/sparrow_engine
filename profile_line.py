from line_profiler import LineProfiler

import sparrow.graphics.integration.extraction as ex
from main import main

lp = LineProfiler()

# Add the function's code object to the profiler registry
lp.add_function(ex.extract_render_frame_system)

try:
    # Execute the entry point through the profiler's trace function
    lp.runcall(main)
finally:
    lp.dump_stats(".debug/extract_render_frame.lprof")
    lp.print_stats()
