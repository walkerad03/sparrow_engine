from pathlib import Path
from typing import Dict

import moderngl


class ShaderManager:
    def __init__(self, ctx: moderngl.Context, shader_dir: Path):
        self.ctx = ctx
        self.dir = Path(shader_dir)
        self._programs: Dict[str, moderngl.Program] = {}

    def get(self, name: str) -> moderngl.Program:
        vert_path = self.dir / f"{name}.vert"
        frag_path = self.dir / f"{name}.frag"

        if not vert_path.exists() or not frag_path.exists():
            raise FileNotFoundError(f"Shader {name} missing in {self.dir}")

        if name not in self._programs:
            self._load(name, vert_path, frag_path)
        return self._programs[name]

    def get_bespoke(
        self, name: str, vert_file: Path | str, frag_file: Path | str
    ) -> moderngl.Program:
        vert_path = self.dir / vert_file
        frag_path = self.dir / frag_file

        if not Path(vert_path).exists():
            print(vert_file)
            raise FileNotFoundError(f"Shader {vert_path} missing in {self.dir}")
        if not Path(frag_path).exists():
            raise FileNotFoundError(f"Shader {frag_path} missing in {self.dir}")

        if name not in self._programs:
            self._load(name, vert_path, frag_path)
        return self._programs[name]

    def _load(self, name: str, vert_path: Path, frag_path: Path):
        """Loads {name}.vert and {name}.frag and compiles them."""

        with open(vert_path, "r") as f:
            vert_src = f.read()
        with open(frag_path, "r") as f:
            frag_src = f.read()

        self._programs[name] = self.ctx.program(
            vertex_shader=vert_src, fragment_shader=frag_src
        )
