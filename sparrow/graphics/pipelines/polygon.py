from typing import Optional

from sparrow.graphics.graph.builder import RenderGraphBuilder
from sparrow.graphics.passes.polygon_2d import Polygon2DPass
from sparrow.graphics.renderer.settings import RendererSettings
from sparrow.graphics.util.ids import PassId, ResourceId


def build_polygon_pipeline(
    builder: RenderGraphBuilder,
    settings: RendererSettings,
    output_target: Optional[ResourceId] = None,
) -> None:
    builder.add_pass(
        PassId("polygon_2d"),
        Polygon2DPass(
            pass_id=PassId("polygon_2d"),
            settings=settings,
        ),
    )
