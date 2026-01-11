#version 330 core

in vec2 v_uv;
out vec4 f_color;

uniform sampler2D u_albedo;
uniform sampler2D u_normal;
uniform sampler2D u_depth;

uniform vec3 u_light_pos;
uniform vec4 u_color;
uniform float u_radius;

uniform mat4 u_inv_view_proj;

uniform vec2 u_resolution;

vec3 reconstruct_world_pos(vec2 uv, float depth) {
    vec4 clip = vec4(uv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
    vec4 world = u_inv_view_proj * clip;
    return world.xyz / world.w;
}

void main() {
    float depth = texture(u_depth, v_uv).r;
    if (depth == 1.0) discard;

    vec3 world_pos = reconstruct_world_pos(v_uv, depth);

    vec3 N = normalize(texture(u_normal, v_uv).rgb * 2.0 - 1.0);
    vec3 L = u_light_pos - world_pos;

    float dist = length(L);
    if (dist > u_radius) discard;

    vec3 light_dir = normalize(L);
    float diffuse = max(dot(N, light_dir), 0.0);

    float attenuation = pow(1.0 - dist / u_radius, 2.0);

    vec4 albedo = texture(u_albedo, v_uv);

    f_color = albedo * u_color * diffuse * attenuation;
}
