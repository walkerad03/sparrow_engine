# sparrow/graphics/graph/resources.py
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol, Sequence, Tuple, Type, TypeVar, cast

import moderngl

from sparrow.graphics.util.ids import ResourceId


class TextureKind(str, Enum):
    """High-level texture categories the graph can manage."""

    TEX2D = "tex2d"
    TEX2D_MSAA = "tex2d_msaa"
    CUBEMAP = "cubemap"


@dataclass(frozen=True, slots=True)
class TextureDesc:
    """
    Declarative texture specification.

    The graph owns allocation and may reallocate on resize.
    """

    width: int
    height: int
    components: int
    dtype: str  # e.g., "f2", "f4", "u1" etc (ModernGL dtype strings)
    kind: TextureKind = TextureKind.TEX2D
    samples: int = 0  # 1+ for MSAA
    mipmaps: bool = False
    label: str = ""
    depth: bool = False  # For depth textures


@dataclass(frozen=True, slots=True)
class BufferDesc:
    """Declarative buffer specification."""

    size_bytes: int
    dynamic: bool = True
    label: str = ""


@dataclass(frozen=True, slots=True)
class FramebufferDesc:
    """Declarative framebuffer specification."""

    color_attachments: tuple[ResourceId, ...]
    depth_attachment: ResourceId | None = None
    label: str = ""


THandle = TypeVar("THandle", covariant=True)


class GraphResource(Protocol[THandle]):
    """Protocol for graph-owned GPU resources."""

    label: str
    handle: THandle


@dataclass(slots=True)
class TextureResource(GraphResource):
    """A graph-owned texture with a stable identity across recompiles when possible."""

    desc: TextureDesc
    handle: moderngl.Texture | moderngl.TextureCube
    label: str


@dataclass(slots=True)
class BufferResource(GraphResource):
    """A graph-owned buffer."""

    desc: BufferDesc
    handle: moderngl.Buffer
    label: str


@dataclass(slots=True)
class FramebufferResource(GraphResource):
    """A graph-owned framebuffer built from attachments."""

    desc: FramebufferDesc
    handle: moderngl.Framebuffer
    label: str


R = TypeVar("R", TextureResource, BufferResource, FramebufferResource)


def expect_resource(
    resources: Mapping[ResourceId, GraphResource[object]],
    rid: ResourceId,
    expected: Type[R],
) -> R:
    res = resources[rid]
    if not isinstance(res, expected):
        raise TypeError(
            f"Resource '{rid}' is {type(res).__name__}, expected {expected.__name__}"
        )
    return cast(R, res)  # ty:ignore[redundant-cast]


def allocate_texture(ctx: moderngl.Context, desc: TextureDesc) -> TextureResource:
    """
    Allocate a texture according to a TextureDesc.

    Raises:
        ValueError: If the descriptor is invalid.
    """
    if desc.width <= 0 or desc.height <= 0:
        raise ValueError("Texture dimensions must be positive")

    if desc.kind == TextureKind.CUBEMAP:
        if desc.width != desc.height:
            raise ValueError("Cubemap textures must be square")
        if desc.samples != 1:
            raise ValueError("Cubemaps do not support MSAA")
        if desc.mipmaps and desc.width & (desc.width - 1) != 0:
            raise ValueError("Cubemap mipmaps require power-of-two size")

        tex = ctx.texture_cube(
            size=(desc.width, desc.height), components=desc.components, dtype=desc.dtype
        )

        if desc.mipmaps:
            tex.build_mipmaps()

    else:
        if desc.samples < 0:
            raise ValueError("samples must be >= 0")

        if desc.mipmaps and desc.samples != 0:
            raise ValueError("MSAA textures cannot have mipmaps")

        if desc.depth:
            tex = ctx.depth_texture(
                size=(desc.width, desc.height),
                samples=desc.samples,
            )
        else:
            tex = ctx.texture(
                size=(desc.width, desc.height),
                components=desc.components,
                dtype=desc.dtype,
                samples=desc.samples,
            )

        if desc.mipmaps:
            tex.build_mipmaps()

        tex.repeat_x = False
        tex.repeat_y = False

    label = desc.label or f"Texture({desc.kind.value})"
    return TextureResource(desc=desc, handle=tex, label=label)


def _assert_fbo_texture(
    tex: moderngl.Texture | moderngl.TextureCube,
) -> moderngl.Texture:
    if isinstance(tex, moderngl.TextureCube):
        raise ValueError("Cubemap textures cannot be attached to framebuffers.")
    return tex


def _tex_info(
    tex: moderngl.Texture | moderngl.TextureCube,
) -> Tuple[Tuple[int, int], int]:
    size = tex.size
    if isinstance(tex, moderngl.TextureCube):
        return size, 1
    return size, tex.samples


def allocate_framebuffer(
    ctx: moderngl.Context,
    *,
    color_attachment_ids: Sequence[ResourceId],
    color_attachments: Sequence[TextureResource],
    depth_attachment_id: ResourceId | None = None,
    depth_attachment: TextureResource | None = None,
    label: str = "",
) -> FramebufferResource:
    """
    Create a framebuffer from texture resources.

    Args:
        color_attachments: Color render targets in draw order.
        depth_attachments: Optional depth texture.
        label: Debug label.

    Raises:
        ValueError: If attachment dimensions or sample counts mismatch.
    """
    if len(color_attachment_ids) != len(color_attachments):
        raise ValueError("color_attachment_ids must match color_attachments length")

    colors = [_assert_fbo_texture(tex.handle) for tex in color_attachments]
    depth = _assert_fbo_texture(depth_attachment.handle) if depth_attachment else None

    ref_size = None
    ref_samples = None

    for tex in colors + ([depth] if depth else []):
        size, samples = _tex_info(tex)

        if ref_size is None:
            ref_size = size
            ref_samples = samples

        else:
            if size != ref_size:
                raise ValueError("Framebuffer attachments must have matching sizes")
            if samples != ref_samples:
                raise ValueError(
                    "Framebuffer attachments must ahve matching sample counts"
                )

    fbo = ctx.framebuffer(color_attachments=colors, depth_attachment=depth)

    fb_desc = FramebufferDesc(
        color_attachments=tuple(color_attachment_ids),
        depth_attachment=depth_attachment_id,
        label=label or "Framebuffer",
    )

    return FramebufferResource(desc=fb_desc, handle=fbo, label=fb_desc.label)
