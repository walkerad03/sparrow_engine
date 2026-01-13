# sparrow/graphics/graph/compilation.py
from __future__ import annotations

import heapq
from collections import defaultdict
from typing import Dict, List, Mapping, Sequence, Set

import moderngl

from sparrow.graphics.graph.builder import RenderGraphBuilder
from sparrow.graphics.graph.pass_base import (
    PassBuildInfo,
    PassResourceUse,
    RenderPass,
    RenderServices,
)
from sparrow.graphics.graph.render_graph import CompiledRenderGraph
from sparrow.graphics.graph.resources import (
    BufferDesc,
    BufferResource,
    FramebufferResource,
    GraphResource,
    TextureDesc,
    TextureResource,
    allocate_framebuffer,
    allocate_texture,
)
from sparrow.graphics.util.ids import PassId, ResourceId


def _fbo_rid(pid: PassId) -> ResourceId:
    """ResourceId used for compiler-generated per-pass framebuffers."""
    return ResourceId(f"fbo:{pid}")


def _all_declared_resources(builder: RenderGraphBuilder) -> Set[ResourceId]:
    return set(builder.textures.keys()) | set(builder.buffers.keys())


def _uses_for_pass(info: PassBuildInfo) -> Sequence[PassResourceUse]:
    return tuple(info.reads) + tuple(info.writes)


def _is_write(access: str) -> bool:
    return access in ("write", "readwrite")


def _is_read(access: str) -> bool:
    return access in ("read", "readwrite")


def _validate_resource_references(
    *, builder: RenderGraphBuilder, pass_infos: Mapping[PassId, PassBuildInfo]
) -> None:
    """
    Validate that every referenced ResourceId exists in the builder.

    Raises:
        KeyError: If a pass references an undeclared resource id.
    """
    declared = _all_declared_resources(builder)

    errors: List[str] = []
    for pid, info in pass_infos.items():
        for use in _uses_for_pass(info):
            if use.resource not in declared:
                errors.append(
                    f"Pass '{pid}' references undeclared resource '{use.resource}' "
                    f"(access={use.access}, stage={use.stage}, binding={use.binding})"
                )

    if errors:
        msg = "Render graph resource validation failed:\n" + "\n".join(
            f"- {e}" for e in errors
        )
        print(msg)
        raise KeyError()


def _build_dependency_dag(
    *, pass_infos: Mapping[PassId, PassBuildInfo]
) -> Dict[PassId, Set[PassId]]:
    """
    Build a conservative dependency DAG based on resource hazards.

    Edges:
        - writer -> reader (RAW)
        - writer -> writer (WAW, serialized deterministically)
        - reader -> writer is NOT added (WAR) because in typical render graphs
        reads do not require ordering unless the same resource is also written.
        If you want WAR safety for specific stages, add it later.

    Returns:
        adjacency: Mapping from pass id to set of dependent pass ids.
    """

    # resource -> passes that read / write (including readwrite)
    readers: Dict[ResourceId, Set[PassId]] = defaultdict(set)
    writers: Dict[ResourceId, Set[PassId]] = defaultdict(set)

    for pid, info in pass_infos.items():
        for use in info.reads:
            if _is_read(use.access):
                readers[use.resource].add(pid)
            if _is_write(use.access):
                writers[use.resource].add(pid)

        for use in info.writes:
            if _is_read(use.access):
                readers[use.resource].add(pid)
            if _is_write(use.access):
                writers[use.resource].add(pid)

    adjacency: Dict[PassId, Set[PassId]] = {pid: set() for pid in pass_infos.keys()}

    # RAW edges: all writers must precede all readers (excluding self)
    for rid, ws in writers.items():
        rs = readers.get(rid, set())
        for w in ws:
            for r in rs:
                if w != r:
                    adjacency[w].add(r)

    # WAW edges: serialize multiple writers deterministically
    # (prevents undefined ordering for write-write hazards)
    for rid, ws in writers.items():
        if len(ws) <= 1:
            continue
        ordered = sorted(ws, key=str)
        for a, b in zip(ordered, ordered[1:]):
            adjacency[a].add(b)

    return adjacency


def _toposort(*, adjacency: Mapping[PassId, Set[PassId]]) -> List[PassId]:
    indeg: Dict[PassId, int] = {pid: 0 for pid in adjacency}

    for dsts in adjacency.values():
        for dst in dsts:
            indeg[dst] += 1

    ready: List[PassId] = [pid for pid, d in indeg.items() if d == 0]
    heapq.heapify(ready)  # PassId is str-like, ordering is well-defined

    out: List[PassId] = []

    while ready:
        pid: PassId = heapq.heappop(ready)
        out.append(pid)

        for nxt in adjacency[pid]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                heapq.heappush(ready, nxt)

    if len(out) != len(indeg):
        remaining = [pid for pid, d in indeg.items() if d > 0]
        raise ValueError(f"Render graph contains a cycle involving: {remaining}")

    return out


def _allocate_textures(
    *, gl: moderngl.Context, textures: Mapping[ResourceId, TextureDesc]
) -> Dict[ResourceId, TextureResource]:
    return {rid: allocate_texture(gl, desc) for rid, desc in textures.items()}


def _allocate_buffers(
    *, gl: moderngl.Context, buffers: Mapping[ResourceId, BufferDesc]
) -> Dict[ResourceId, BufferResource]:
    """
    Allocate buffers from BufferDesc.

    Note:
        This assumes BufferDesc has at least: size: int, label: str.
    """
    out: Dict[ResourceId, BufferResource] = {}
    for rid, desc in buffers.items():
        # reserve GPU storage
        size = getattr(desc, "size_bytes", None)
        if not isinstance(size, int) or size <= 0:
            raise ValueError(
                f"BufferDesc for '{rid}' must define a positive 'size' int"
            )
        buf = gl.buffer(reserve=size)
        buf_res = BufferResource(desc=desc, handle=buf, label="Buffer")
        out[rid] = buf_res
    return out


def _allocate_pass_framebuffers(
    *,
    gl: moderngl.Context,
    order: Sequence[PassId],
    pass_infos: Mapping[PassId, PassBuildInfo],
    textures: Mapping[ResourceId, TextureResource],
) -> Dict[ResourceId, FramebufferResource]:
    """
    Allocate per-pass framebuffers based on declared writes.

    Convention:
      - stage == "color" and access includes write => color attachment
      - stage == "depth" and access includes write => depth attachment (single)

    A pass with no color/depth writes receives no framebuffer.
    """
    fbos: Dict[ResourceId, FramebufferResource] = {}

    for pid in order:
        info = pass_infos[pid]

        color_rids: List[ResourceId] = []
        depth_rid: ResourceId | None = None

        for use in info.writes:
            if not _is_write(use.access):
                continue
            if use.stage == "color":
                color_rids.append(use.resource)
            elif use.stage == "depth":
                depth_rid = use.resource

        if not color_rids and depth_rid is None:
            continue  # compute-only pass or pass writing only buffers, etc.

        color_tex = [textures[rid] for rid in color_rids]
        depth_tex = textures[depth_rid] if depth_rid is not None else None

        fbo = allocate_framebuffer(
            gl,
            color_attachments=color_tex,
            depth_attachment=depth_tex,
            label=f"fbo:{pid}",
        )
        fbos[_fbo_rid(pid)] = fbo

    return fbos


def _call_on_graph_compiled(
    *,
    gl: moderngl.Context,
    order: Sequence[PassId],
    passes: Mapping[PassId, RenderPass],
    resources: Mapping[ResourceId, GraphResource[object]],
    services: RenderServices,
) -> None:
    """
    Call on_graph_compiled for each pass in execution order.

    If a pass throws, previously-initialized passes are not automatically rolled back.
    """
    for pid in order:
        passes[pid].on_graph_compiled(ctx=gl, resources=resources, services=services)


def compile_render_graph(
    *,
    gl: moderngl.Context,
    builder: RenderGraphBuilder,
    services: RenderServices,
) -> CompiledRenderGraph:
    """
    Compile a RenderGraphBuilder into an executable CompiledRenderGraph.

    Responsibilities:
        - allocate textures/buffers/fbos
        - validate pass resource uses
        - compute pass order (topological sort)
        - call pass.on_graph_compiled
    """
    # Collect build info for each pass
    pass_infos: Dict[PassId, PassBuildInfo] = {}
    for pid, p in builder.passes.items():
        info = p.build()
        # Ensure the pass's declared id matches the key it is stored under.
        if info.pass_id != pid:
            raise ValueError(
                f"Pass stored under id '{pid}' returned build().pass_id='{info.pass_id}'"
            )
        pass_infos[pid] = info

    _validate_resource_references(builder=builder, pass_infos=pass_infos)

    adjacency = _build_dependency_dag(pass_infos=pass_infos)

    order = _toposort(adjacency=adjacency)

    tex_resources = _allocate_textures(gl=gl, textures=builder.textures)
    buf_resources = _allocate_buffers(gl=gl, buffers=builder.buffers)
    fbo_resources = _allocate_pass_framebuffers(
        gl=gl,
        order=order,
        pass_infos=pass_infos,
        textures=tex_resources,
    )

    resources: Dict[ResourceId, GraphResource[object]] = {}
    resources.update(tex_resources)
    resources.update(fbo_resources)
    resources.update(buf_resources)

    _call_on_graph_compiled(
        gl=gl,
        order=order,
        passes=builder.passes,
        resources=resources,
        services=services,
    )

    return CompiledRenderGraph(
        gl=gl,
        pass_order=order,
        passes=dict(builder.passes),
        resources=resources,
        services=services,
    )
