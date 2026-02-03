# sparrow/graphics/pipelines/standard_3d.py

from sparrow.graphics.graph import FramebufferDesc, TextureDesc
from sparrow.graphics.graph.builder import RenderGraphBuilder
from sparrow.graphics.passes.clear import ClearPass
from sparrow.graphics.passes.forward import ForwardPBRPass
from sparrow.graphics.passes.tonemap import TonemapPass
from sparrow.graphics.utils.ids import PassId, ResourceId


def build_standard_3d_pipeline(builder: RenderGraphBuilder) -> None:
    """
    Constructs a basic Forward PBR pipeline.
    """

    builder.define_texture(
        ResourceId("hdr_color"),
        desc=TextureDesc(
            components=4,
            dtype="f2",
        ),
    )

    builder.define_texture(
        ResourceId("depth_stencil"),
        desc=TextureDesc(
            components=1,
            dtype="f4",
            is_depth=True,
        ),
    )

    builder.define_framebuffer(
        ResourceId("main_fbo"),
        FramebufferDesc(
            color_attachments=[ResourceId("hdr_color")],
            depth_attachment=ResourceId("depth_stencil"),
        ),
    )

    builder.add_pass(
        ClearPass(
            pass_id=PassId("clear_pass"),
            target=ResourceId("main_fbo"),
            color=(0.1, 0.1, 0.1, 1.0),
        )
    )

    builder.add_pass(
        ForwardPBRPass(
            pass_id=PassId("forward_pass"),
            target=ResourceId("main_fbo"),
        )
    )

    builder.add_pass(
        TonemapPass(
            pass_id=PassId("tonemap"),
            input_texture=ResourceId("hdr_color"),
            target=None,
        )
    )
