#version 330 core

in vec2 v_uv;

// G-Buffer Samplers
uniform sampler2D u_albedo;
uniform sampler2D u_normal;
uniform sampler2D u_occlusion;

// Light Data
uniform vec2 u_light_pos;
uniform vec3 u_light_color;
uniform float u_light_radius;
uniform float u_intensity;
uniform vec3 u_ambient;

out vec4 f_color;

void main() {
    // 1. Read G-Buffer
    vec4 albedo = texture(u_albedo, v_uv);
    vec3 normal = texture(u_normal, v_uv).rgb;
    
    // If alpha is 0 (empty space), discard
    if (albedo.a < 0.1) discard;

    // 2. Simple Distance Attenuation
    // (In a real deferred renderer, we calculate pixel position from depth,
    // but for 2D sprites, we can cheat a bit or pass screen coords).
    
    // Placeholder: Just output the Albedo * Ambient for now 
    // to prove the G-Buffer works.
    vec3 final_color = albedo.rgb * u_ambient;
    
    // Basic Additive Light (Very rough approximation for testing)
    final_color += albedo.rgb * u_light_color * u_intensity * 0.1;

    f_color = vec4(final_color, albedo.a);
}