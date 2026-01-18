from sparrow.graphics.graph.builder import RenderGraphBuilder
from sparrow.graphics.graph.resources import TextureDesc
from sparrow.graphics.passes.debug_present import DebugPresentPass
from sparrow.graphics.passes.forward_unlit import ForwardUnlitPass
from sparrow.graphics.renderer.settings import BlitRendererSettings
from sparrow.graphics.util.ids import PassId, ResourceId


def build_blit_pipeline(builder: RenderGraphBuilder, settings: BlitRendererSettings):
    width, height = (
        settings.resolution.logical_width,
        settings.resolution.logical_height,
    )

    builder.add_texture(
        ResourceId("g_albedo"),
        TextureDesc(width, height, 4, "f2"),
    )
    builder.add_texture(
        ResourceId("g_depth"),
        TextureDesc(width, height, 1, "f4", depth=True),
    )

    pid = PassId("gbuffer")
    builder.add_pass(
        pid,
        ForwardUnlitPass(
            pid,
            ResourceId("g_albedo"),
            ResourceId("g_depth"),
        ),
    )

    pid = PassId("debug_present")
    builder.add_pass(
        pid,
        DebugPresentPass(
            pid,
            source_tex=ResourceId("g_albedo"),
        ),
    )
