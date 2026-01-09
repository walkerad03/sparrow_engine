#version 330 core

in vec2 v_uv;

// Uniforms
uniform vec4 u_color;
uniform sampler2D u_texture;

// Outputs to the Framebuffer
layout (location = 0) out vec4 out_albedo;
layout (location = 1) out vec4 out_normal;
layout (location = 2) out float out_occlusion;

void main() {
    // We must use v_uv on windows to keep the compiler from dropping it.
    vec4 tex_color = texture(u_texture, v_uv);
    vec4 final_color = tex_color * u_color;
    if (final_color.a < 0.1) discard;
    
    // Target 0: Albedo (Color)
    out_albedo = final_color;
    
    // Target 1: Normal Map (Flat "Up" vector 0,0,1 for 2D)
    out_normal = vec4(0.5, 0.5, 1.0, 1.0);
    
    // Target 2: Occlusion (1.0 = Blocks Light, 0.0 = Pass Through)
    out_occlusion = 1.0; 
}