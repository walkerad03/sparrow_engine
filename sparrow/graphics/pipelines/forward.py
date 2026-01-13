# sparrow/graphics/pipelines/forward.py
from sparrow.graphics.graph.builder import RenderGraphBuilder
from sparrow.graphics.graph.resources import FramebufferDesc, TextureDesc
from sparrow.graphics.passes.forward_unlit import ForwardUnlitPass
from sparrow.graphics.passes.tonemap import TonemapPass
from sparrow.graphics.util.ids import PassId, ResourceId


def build_forward_pipeline(builder: RenderGraphBuilder, width: int, height: int):
    # 1. Main HDR Color Buffer & Depth
    builder.add_texture(
        ResourceId("main_color"), TextureDesc(width, height, 4, "f2", label="MainColor")
    )
    builder.add_texture(
        ResourceId("main_depth"),
        TextureDesc(width, height, 1, "f4", depth=True, label="Depth"),
    )

    pid = "forward_main"
    builder.add_framebuffer(
        ResourceId(pid),
        FramebufferDesc(
            color_attachments=(ResourceId("main_color"),),
            depth_attachment=ResourceId("main_depth"),
            label="Forward Main FBO",
        ),
    )

    # 2. Forward Pass (Draws meshes directly to main_color)
    builder.add_pass(
        PassId(pid),
        ForwardUnlitPass(
            pass_id=PassId(pid),
            color_target=ResourceId("main_color"),
            depth_target=ResourceId("main_depth"),
        ),
    )

    # 3. Tonemap to Screen
    builder.add_pass(
        PassId("tonemap"),
        TonemapPass(pass_id=PassId("tonemap"), hdr_input=ResourceId("main_color")),
    )
