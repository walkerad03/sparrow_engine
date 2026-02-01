from typing import Optional

from sparrow.graphics.graph.builder import RenderGraphBuilder
from sparrow.graphics.passes.blit import BlitPass
from sparrow.graphics.renderer.settings import RendererSettings
from sparrow.graphics.util.ids import PassId, ResourceId, TextureId


def build_blit_pipeline(
    builder: RenderGraphBuilder,
    settings: RendererSettings,
    output_target: Optional[ResourceId] = None,
) -> None:
    builder.add_pass(
        PassId("blit"),
        BlitPass(
            pass_id=PassId("blit"),
            settings=settings,
            texture_id=TextureId("engine.splashscreen"),
        ),
    )
