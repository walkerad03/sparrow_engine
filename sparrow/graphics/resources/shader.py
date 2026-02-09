# sparrow/graphics/resources/shader.py
from typing import Dict, Optional, Tuple

import moderngl

from sparrow.assets import AssetHandle, AssetServer


class ShaderManager:
    """
    Manages shader compilation and include libraries.
    """

    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        self._programs: Dict[str, moderngl.Program] = {}
        self._handle_cache: Dict[Tuple[int, int], moderngl.Program] = {}

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
        defines_str = str(sorted(defines.items())) if defines else ""
        key = f"{vert_source}|{frag_source}|{defines_str}"

        if key in self._programs:
            return self._programs[key]

        try:
            program = self.ctx.program(
                vertex_shader=vert_source, fragment_shader=frag_source
            )
            self._programs[key] = program
            return program

        except moderngl.Error as e:
            print(f"Shader Compilation Failed: {e}")
            raise

    def get_program_from_assets(
        self,
        asset_server: AssetServer,
        vs_handle: AssetHandle,
        fs_handle: AssetHandle,
        defines: Optional[Dict[str, str]] = None,
    ) -> Optional[moderngl.Program]:
        key = (vs_handle.id, fs_handle.id)

        if key in self._handle_cache:
            return self._handle_cache[key]

        if not (
            asset_server.is_ready(vs_handle)
            and asset_server.is_ready(fs_handle)
        ):
            return None

        vs_data = asset_server.get_data(vs_handle)
        fs_data = asset_server.get_data(fs_handle)

        vs_src = vs_data.source if hasattr(vs_data, "source") else vs_data
        fs_src = fs_data.source if hasattr(fs_data, "source") else fs_data

        program = self.get_program(vs_src, fs_src, defines)
        self._handle_cache[key] = program

        return program

    def release(self) -> None:
        for prog in self._programs.values():
            prog.release()
        self._programs.clear()
        self._handle_cache.clear()
