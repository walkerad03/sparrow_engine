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
    if not isinstance(settings, ForwardRendererSettings):
        raise TypeError(
            f"build_forward_pipeline expects ForwardRendererSettings, got {type(settings)!r}"
        )

    albedo = builder.add_texture(
        ResourceId("albedo"),
        TextureDesc(
            settings.resolution.logical_width,
            settings.resolution.logical_height,
            4,
            "f2",
        ),
    )

    depth = builder.add_texture(
        ResourceId("depth"),
        TextureDesc(
            settings.resolution.logical_width,
            settings.resolution.logical_height,
            1,
            "f4",
            depth=True,
        ),
    )

    builder.add_pass(
        PassId("forward"),
        ForwardPass(
            pass_id=PassId("forward"),
            settings=settings,
            albedo_tex=albedo,
            depth_tex=depth,
        ),
    )

    builder.add_pass(
        PassId("present"),
        TonemapPass(
            pass_id=PassId("present"),
            hdr_in=albedo,
            settings=settings,
        ),
    )
