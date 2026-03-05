#version 460 core

uniform sampler2D u_color_tex;
uniform sampler2D u_depth_tex;

uniform vec3 u_fog_color;
uniform float u_fog_density;
uniform float u_near;
uniform float u_far;

in vec2 v_uv;
out vec4 fragColor;

float linearize_depth(float depth, float near_plane, float far_plane) {
    float z_ndc = depth * 2.0 - 1.0;
    return (2.0 * near_plane * far_plane) /
           (far_plane + near_plane - z_ndc * (far_plane - near_plane));
}

void main() {
    vec3 color = texture(u_color_tex, v_uv).rgb;
    float depth = texture(u_depth_tex, v_uv).r;

    float near_plane = max(u_near, 0.0001);
    float far_plane = max(u_far, near_plane + 0.0001);
    float view_distance = linearize_depth(depth, near_plane, far_plane);

    // Beer-Lambert law: transmittance = exp(-density * distance)
    float transmittance = exp(-u_fog_density * view_distance);
    float fog_factor = clamp(1.0 - transmittance, 0.0, 1.0);

    vec3 fogged = mix(color, u_fog_color, fog_factor);
    fragColor = vec4(fogged, 1.0);
}
