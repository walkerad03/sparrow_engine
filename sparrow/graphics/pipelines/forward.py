# sparrow/graphics/pipelines/forward.py
from sparrow.graphics.graph.builder import RenderGraphBuilder
from sparrow.graphics.graph.resources import TextureDesc
from sparrow.graphics.passes.forward import ForwardPass
from sparrow.graphics.passes.tonemap import TonemapPass
from sparrow.graphics.renderer.settings import ForwardRendererSettings
from sparrow.graphics.util.ids import PassId, ResourceId


def build_forward_pipeline(
    builder: RenderGraphBuilder, settings: ForwardRendererSettings
):
    width, height = (
        settings.resolution.logical_width,
        settings.resolution.logical_height,
    )

    albedo_rid = builder.add_texture(
        ResourceId("albedo"), TextureDesc(width, height, 4, "f2", label="MainColor")
    )
    depth_rid = builder.add_texture(
        ResourceId("depth"),
        TextureDesc(width, height, 1, "f4", depth=True, label="Depth"),
    )

    pid = PassId("forward")
    builder.add_pass(
        pid,
        ForwardPass(
            pass_id=pid,
            out_albedo=albedo_rid,
            out_depth=depth_rid,
        ),
    )

    pid = PassId("tonemap")
    builder.add_pass(
        pid,
        TonemapPass(
            pass_id=pid,
            hdr_in=albedo_rid,
        ),
    )
