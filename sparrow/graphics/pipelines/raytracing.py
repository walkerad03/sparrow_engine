# sparrow/graphics/pipelines/raytracing.py
from sparrow.graphics.graph.builder import RenderGraphBuilder
from sparrow.graphics.graph.resources import TextureDesc
from sparrow.graphics.passes.raytracing import RaytracingPass
from sparrow.graphics.passes.tonemap import TonemapPass
from sparrow.graphics.renderer.settings import RaytracingRendererSettings
from sparrow.graphics.util.ids import PassId, ResourceId


def build_raytracing_pipeline(
    builder: RenderGraphBuilder, settings: RaytracingRendererSettings
):
    if not isinstance(settings, RaytracingRendererSettings):
        raise TypeError("Expected RaytracingRendererSettings for raytrace pipeline")

    out_tex_rid = builder.add_texture(
        ResourceId("rt_output"),
        TextureDesc(
            settings.resolution.logical_width,
            settings.resolution.logical_height,
            4,
            "f2",
            label="RTOutput",
        ),
    )

    pid = PassId("raytrace_step")
    builder.add_pass(
        pid,
        RaytracingPass(
            pass_id=pid,
            settings=settings,
            out_texture=out_tex_rid,
        ),
    )

    pid = PassId("present")
    builder.add_pass(
        pid,
        TonemapPass(
            pass_id=pid,
            hdr_in=out_tex_rid,
        ),
    )
