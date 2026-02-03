# sparrow/graphics/resources/shader.py
from typing import Dict, Optional

import moderngl


class ShaderManager:
    """
    Manages shader compilation and include libraries.
    """

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self._programs: Dict[str, moderngl.Program] = {}

        self._init_includes()

    def _init_includes(self) -> None:
        """Register global shader includes."""

        # TODO: Actual common library support
        # Example of a common library available to all shaders via #include "common.glsl"
        self.ctx.includes["common.glsl"] = """
        struct Light {
            vec3 position;
            float radius;
            vec3 color;
            float intensity;
            int shadow_map_id;
        };

        float calculate_attenuation(float dist, float radius) {
            float d = max(dist, 0.001);
            return max(0.0, 1.0 - (d / radius));
        }
        """

    def get_program(
        self,
        vert_source: str,
        frag_source: str,
        defines: Optional[Dict[str, str]] = None,
    ) -> moderngl.Program:
        """
        Compile or retrieve a cached program.
        """
        key = hash(
            (
                vert_source,
                frag_source,
                tuple(defines.items()) if defines else None,
            )
        )

        if key in self._programs:
            return self._programs[str(key)]

        header = "#version 460 core\n"
        if defines:
            for k, v in defines.items():
                header += f"#define {k} {v}\n"

        try:
            program = self.ctx.program(
                vertex_shader=vert_source, fragment_shader=frag_source
            )
            self._programs[str(key)] = program
            return program
        except moderngl.Error as e:
            print(f"Shader Compilation Failed: {e}")
            raise

    def release(self) -> None:
        for prog in self._programs.values():
            prog.release()
        self._programs.clear()
