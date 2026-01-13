from sparrow.graphics.graph.builder import RenderGraphBuilder
from sparrow.graphics.graph.resources import FramebufferDesc, TextureDesc
from sparrow.graphics.passes.deferred_lighting import DeferredLightingPass
from sparrow.graphics.passes.gbuffer import GBufferPass
from sparrow.graphics.passes.tonemap import TonemapPass
from sparrow.graphics.util.ids import PassId, ResourceId


def build_deferred_pipeline(builder: RenderGraphBuilder, width: int, height: int):
    builder.add_texture(
        ResourceId("g_albedo"),
        TextureDesc(
            width,
            height,
            4,
            "f2",
            label="Albedo",
        ),
    )
    builder.add_texture(
        ResourceId("g_normal"),
        TextureDesc(
            width,
            height,
            4,
            "f2",
            label="Normal",
        ),
    )
    builder.add_texture(
        ResourceId("g_orm"),
        TextureDesc(
            width,
            height,
            4,
            "f2",
            label="ORM",
        ),
    )
    builder.add_texture(
        ResourceId("g_depth"),
        TextureDesc(
            width,
            height,
            1,
            "f4",
            depth=True,
            label="Depth",
        ),
    )

    builder.add_framebuffer(
        ResourceId("gbuffer_fbo"),
        FramebufferDesc(
            color_attachments=(
                ResourceId("g_albedo"),
                ResourceId("g_normal"),
                ResourceId("g_orm"),
            ),
            depth_attachment=ResourceId("g_depth"),
        ),
    )

    builder.add_pass(
        PassId("gbuffer"),
        GBufferPass(
            pass_id=PassId("gbuffer"),
            g_albedo=ResourceId("g_albedo"),
            g_normal=ResourceId("g_normal"),
            g_orm=ResourceId("g_orm"),
            g_depth=ResourceId("g_depth"),
        ),
    )

    builder.add_texture(
        ResourceId("light_accum"),
        TextureDesc(
            width,
            height,
            4,
            "f2",
            label="LightAccum",
        ),
    )

    builder.add_framebuffer(
        ResourceId("light_fbo"),
        FramebufferDesc(
            (ResourceId("light_accum"),),
            depth_attachment=None,
        ),
    )

    builder.add_pass(
        PassId("deferred_lighting"),
        DeferredLightingPass(
            pass_id=PassId("deferred_lighting"),
            out_fbo=ResourceId("light_fbo"),
            light_accum=ResourceId("light_accum"),
            g_albedo=ResourceId("g_albedo"),
            g_normal=ResourceId("g_normal"),
            g_orm=ResourceId("g_orm"),
            g_depth=ResourceId("g_depth"),
        ),
    )

    builder.add_pass(
        PassId("tonemap"),
        TonemapPass(
            pass_id=PassId("tonemap"),
            hdr_input=ResourceId("light_accum"),
        ),
    )
