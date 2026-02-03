# sparrow/graphics/pipelines/standard_3d.py
from sparrow.graphics.graph.builder import RenderGraphBuilder
from sparrow.graphics.passes.clear import ClearPass
from sparrow.graphics.passes.forward import ForwardPBRPass
from sparrow.graphics.utils.ids import PassId


def build_standard_3d_pipeline(builder: RenderGraphBuilder) -> None:
    """
    Constructs a basic Forward PBR pipeline.
    """

    builder.add_pass(
        ClearPass(
            pass_id=PassId("clear_pass"),
            color=(0.1, 0.1, 0.12, 1.0),
        )
    )

    builder.add_pass(
        ForwardPBRPass(
            pass_id=PassId("forward_pass"),
            target=None,
        )
    )
