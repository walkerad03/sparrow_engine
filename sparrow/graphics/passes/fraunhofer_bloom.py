# sparrow/graphics/passes/fraunhofer_bloom.py
import math
from dataclasses import dataclass
from typing import Mapping

import moderngl

from sparrow.graphics.graph.pass_base import (
    PassBuildInfo,
    PassExecutionContext,
    PassResourceUse,
    RenderPass,
    RenderServices,
)
from sparrow.graphics.graph.resources import (
    GraphResource,
    TextureResource,
    expect_resource,
)
from sparrow.graphics.shaders.program_types import ShaderStages
from sparrow.graphics.shaders.shader_manager import ShaderRequest
from sparrow.graphics.util.ids import PassId, ResourceId, ShaderId, TextureId


@dataclass(kw_only=True)
class FraunhoferBloomPass(RenderPass):
    pass_id: PassId

    input_hdr: ResourceId
    output_bloom: ResourceId
    aperture_tex_id: TextureId

    _program: moderngl.ComputeShader | None = None

    def build(self) -> PassBuildInfo:
        return PassBuildInfo(
            pass_id=self.pass_id,
            name="FraunhoferBloom",
            reads=[PassResourceUse(self.input_hdr, "read", "sampled", binding=0)],
            writes=[PassResourceUse(self.output_bloom, "write", "storage", binding=0)],
        )

    def on_graph_compiled(
        self,
        *,
        ctx: moderngl.Context,
        resources: Mapping[ResourceId, GraphResource[object]],
        services: RenderServices,
    ) -> None:
        req = ShaderRequest(
            shader_id=ShaderId("bloom_fraunhofer"),
            stages=ShaderStages(
                compute="sparrow/graphics/shaders/default/bloom_fraunhofer.comp",
            ),
            label="Fraunhofer Bloom",
        )

        resource = services.shader_manager.get(req)
        assert isinstance(resource.program, moderngl.ComputeShader)
        self._program = resource.program

        self._aperture_tex = services.texture_manager.get(self.aperture_tex_id)

    def execute(self, exec_ctx: PassExecutionContext) -> None:
        self.execute_base(exec_ctx)

        resources = exec_ctx.resources

        if not self._program:
            return

        in_tex = expect_resource(resources, self.input_hdr, TextureResource)
        in_tex.handle.use(location=0)

        self._aperture_tex.texture.use(location=1)

        out_tex = expect_resource(resources, self.output_bloom, TextureResource)
        out_tex.handle.bind_to_image(0, read=False, write=True)

        if "u_input_hdr" in self._program:
            self._program["u_input_hdr"] = 0
        if "u_aperture" in self._program:
            self._program["u_aperture"] = 1

        w, h = out_tex.desc.width, out_tex.desc.height
        gw, gh = 16, 16

        nx = int(math.ceil(w / gw))
        ny = int(math.ceil(h / gh))

        self._program.run(nx, ny, 1)

    def on_graph_destroyed(self) -> None:
        self._program = None
