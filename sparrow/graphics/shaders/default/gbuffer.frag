#version 460

layout(location = 0) out vec4 out_albedo;
layout(location = 1) out vec4 out_normal;
layout(location = 2) out vec4 out_orm;

in vec3 v_normal;
in vec2 v_uv;

uniform vec4 u_base_color;
uniform float u_roughness;
uniform float u_metalness;

void main() {
    out_albedo = u_base_color;

    out_normal = vec4(normalize(v_normal) * 0.5 + 0.5, 1.0);

    out_orm = vec4(1.0, u_roughness, u_metalness, 1.0);
}
