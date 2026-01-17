from sparrow.graphics.graph.builder import RenderGraphBuilder
from sparrow.graphics.graph.resources import TextureDesc
from sparrow.graphics.passes.deferred_lighting import DeferredLightingPass
from sparrow.graphics.passes.gbuffer import GBufferPass
from sparrow.graphics.passes.tonemap import TonemapPass
from sparrow.graphics.renderer.settings import DeferredRendererSettings
from sparrow.graphics.util.ids import PassId, ResourceId


def build_deferred_pipeline(
    builder: RenderGraphBuilder, settings: DeferredRendererSettings
) -> None:
    if not isinstance(settings, DeferredRendererSettings):
        raise TypeError(
            f"build_deferred_pipeline expects DeferredRendererSettings, got {type(settings)!r}"
        )

    w, h = (
        settings.resolution.logical_width,
        settings.resolution.logical_height,
    )

    g_albedo = builder.add_texture(
        ResourceId("g_albedo"),
        TextureDesc(w, h, 4, "f2"),
    )
    g_normal = builder.add_texture(
        ResourceId("g_normal"),
        TextureDesc(w, h, 4, "f2"),
    )
    g_orm = builder.add_texture(
        ResourceId("g_orm"),
        TextureDesc(w, h, 4, "f2"),
    )
    g_depth = builder.add_texture(
        ResourceId("g_depth"),
        TextureDesc(w, h, 1, "f4", depth=True),
    )
    light_accum = builder.add_texture(
        ResourceId("light_accum"),
        TextureDesc(w, h, 4, "f2"),
    )

    builder.add_pass(
        PassId("gbuffer"),
        GBufferPass(
            pass_id=PassId("gbuffer"),
            settings=settings,
            g_albedo=g_albedo,
            g_normal=g_normal,
            g_orm=g_orm,
            g_depth=g_depth,
        ),
    )

    builder.add_pass(
        PassId("deferred_lighting"),
        DeferredLightingPass(
            pass_id=PassId("deferred_lighting"),
            settings=settings,
            light_accum=light_accum,
            g_albedo=g_albedo,
            g_normal=g_normal,
            g_orm=g_orm,
            g_depth=g_depth,
        ),
    )

    builder.add_pass(
        PassId("tonemap"),
        TonemapPass(
            pass_id=PassId("tonemap"),
            settings=settings,
            hdr_in=light_accum,
        ),
    )
