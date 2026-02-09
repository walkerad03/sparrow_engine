# 1. Component Breakdown

We are splitting the architecture into three distinct domains: **Assets** (Data on Disk/CPU), **Graphics Core** (Data on GPU/Context), and **Integration** (The Bridge to ECS).

## A. The Asset Domain (`sparrow.assets`)

* **AssetServer:** The central authority. It manages the lifecycle of assets using integer GUIDs (`AssetId`). It handles threading for disk I/O.
* **Importers:** Specialized classes that parse raw bytes into Engine Data Types (e.g., `OBJImporter`, `PNGImporter`, `GLSLImporter`).
* **AssetRegistry:** A lookup table mapping `AssetId`  `AssetData` (CPU memory).

## B. The Graphics Core (`sparrow.graphics`)

* **Renderer:** The main entry point. Owns the Window, the Context, and the active `RenderGraph`.
* **GPUResourceManager:** The GPU-side mirror of the AssetServer. It maps `AssetId`  `moderngl.Buffer` / `moderngl.Texture`. It handles the upload from CPU to GPU.
* **MaterialSystem:**
* `ShaderTemplate`: A compiled shader program with defined inputs.
* `MaterialInstance`: A specific set of uniform values (e.g., "Red Plastic") linked to a Template.


* **RenderGraph:** A Directed Acyclic Graph (DAG) where nodes are `RenderPasses` and edges are `Resources` (Textures/Buffers).
* **RenderPass:** A single execution unit (e.g., `ForwardPass`, `ShadowMapPass`). It defines what it *Reads* and what it *Writes*.
* **ShaderLibrary:** Manages global shader includes (`common.glsl`) and hot-reloading.

## C. The Integration Domain (`sparrow.graphics.integration`)

* **RenderFrame:** A snapshot of the game state optimized for rendering. It contains flat arrays of transforms, material IDs, and mesh IDs. This completely decouples game logic from rendering logic.
* **FrameBuilder:** A system that queries the ECS and populates the `RenderFrame`.

---

# 2. Interaction Flow (The "Frame Lifecycle")

This explains technically how a single frame is produced, from disk to screen.

## Step 1: Asset Loading (Async)

1. **Request:** Game logic calls `assets.load("ship.obj")`.
2. **Handle:** The `AssetServer` hashes the path to generate a `u64` GUID. It immediately returns an `AssetHandle(guid)`.
3. **IO Thread:** Checks if the GUID is loaded. If not, reads the file, parses vertices/indices, and stores them in `CPU RAM` in the registry.
4. **Sync Point:** At the start of the next frame, the `GPUResourceManager` detects a new entry in the registry. It creates a `moderngl.Buffer`, uploads the data, and caches the `gl_buffer_id`.

## Step 2: Extraction (Main Thread / ECS Update)

The simulation runs. We do not render yet; we **extract**.

1. The `RenderingSystem` runs.
2. It queries visible entities (e.g., `Query(World, Transform, Mesh, Material)`).
3. It writes data into a `RenderFrame` object:
* `transforms`: A numpy array of `mat4`.
* `material_ids`: An array of integers.
* `mesh_ids`: An array of integers.
* `camera_data`: View/Proj matrices.
* `lights`: A list of light structs.


4. This `RenderFrame` is immutable and passed to the Renderer. *This allows the next simulation step to start immediately on a separate thread if we add multiprocessing later.*

## Step 3: Preparation (The "Material Sort")

The `Renderer` takes the `RenderFrame`.

1. **Sorting:** To minimize OpenGL state changes, the renderer sorts the draw calls.
* Primary Key: `Pipeline/Pass` (Opaque vs Transparent).
* Secondary Key: `MaterialTemplate` (Shader Program).
* Tertiary Key: `MeshID` (Vertex Array).


2. **Batching:** It groups instances. If 50 objects use "Red Plastic" and the "Cube Mesh", they are grouped into a single **Instanced Draw Call**.

## Step 4: Graph Execution

The `GraphExecutor` iterates through the topological sort of the `RenderGraph`.

1. **Pass Setup:** The executor checks the `RenderPass` definition.
* It binds the output Framebuffer (FBO).
* It binds input Textures (e.g., Shadow Maps from a previous pass) to texture units.


2. **Execution:** The `RenderPass.execute(ctx, frame)` method is called.
* The pass iterates the sorted batches from Step 3.
* `ctx.program["u_view_proj"].write(frame.camera.view_proj)`
* `batch.vao.render(instances=batch.count)`


3. **Composition:** Final passes (Bloom, Tonemap) read the textures written by previous passes and draw a fullscreen quad to the screen.

---

# 3. Proposed File Structure

This structure enforces the separation of Data (`assets`), Core Logic (`graphics/core`), and Implementation (`graphics/passes`).

```text
sparrow/
├── assets/                     # NEW: Top-level Asset Module
│   ├── __init__.py
│   ├── server.py               # Async loading logic & registry
│   ├── handle.py               # AssetHandle(int) definition
│   ├── importers/              # Logic to parse files
│   │   ├── mesh_importer.py
│   │   ├── texture_importer.py
│   │   └── shader_importer.py
│   └── defaults/               # Built-in engine assets (meshes/shaders)
│
├── graphics/
│   ├── __init__.py
│   │
│   ├── core/                   # The Heart
│   │   ├── renderer.py         # Main entry point
│   │   ├── window.py           # Window/Context creation
│   │   ├── interface.py        # Public API for the engine
│   │   └── settings.py         # Resolution, VSync, etc.
│   │
│   ├── resources/              # GPU Wrappers (The AssetServer's GPU counterpart)
│   │   ├── manager.py          # Uploads CPU assets to GPU
│   │   ├── buffer.py           # VBO/IBO/SSBO wrappers
│   │   ├── texture.py          # Texture/Sampler wrappers
│   │   └── shader.py           # Program/Include handling
│   │
│   ├── materials/              # The Material System
│   │   ├── template.py         # MaterialType (Shader + Layout)
│   │   └── instance.py         # MaterialInstance (Values)
│   │
│   ├── graph/                  # The Render Graph
│   │   ├── definition.py       # The Data Structure (Nodes/Links)
│   │   ├── builder.py          # Fluent API to build graphs
│   │   ├── executor.py         # Logic to run the graph
│   │   └── pass_base.py        # Base class for all passes
│   │
│   ├── passes/                 # Implementations
│   │   ├── clear.py
│   │   ├── forward.py
│   │   ├── deferred.py
│   │   ├── post_process.py
│   │   └── ui.py
│   │
│   ├── pipelines/              # Presets
│   │   ├── standard_2d.py
│   │   └── standard_3d.py
│   │
│   ├── integration/            # ECS Bridge
│   │   ├── frame.py            # RenderFrame Data Class
│   │   ├── extraction.py       # System to build RenderFrame
│   │   └── components.py       # Renderable, Light, Camera components
│   │
│   └── utils/                  # GL Helpers
│       ├── geometry.py         # Fullscreen quad, Cube, etc.
│       └── uniforms.py         # Struct packing helpers

```

# 4. TODO
- [ ] sparrow
- [x] .assets
  - [x] .importers
  - [x] .defaults
- [ ] .graphics
  - [x] .core
  - [x] .resources
  - [x] .materials
  - [x] .graph
  - [ ] .passes
  - [ ] .pipelines
  - [x] .integration
  - [x] .utils
