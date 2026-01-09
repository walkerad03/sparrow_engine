#version 330 core

in vec2 v_uv;

// Uniforms
uniform vec4 u_color;
uniform sampler2D u_texture;
uniform float u_blocks_light;

// Outputs to the Framebuffer
layout (location = 0) out vec4 out_albedo;
layout (location = 1) out vec4 out_normal;
layout (location = 2) out vec4 out_occlusion;

void main() {
    vec4 tex_color = texture(u_texture, v_uv);
    if (tex_color.a < 0.1) discard;
    
    out_albedo = tex_color * u_color;
    out_normal = vec4(0.5, 0.5, 1.0, 1.0); // Target 1: Normal Map (Flat "Up" vector 0,0,1 for 2D)
    out_occlusion = vec4(u_blocks_light, 0.0, 0.0, 1.0); // Target 2: Occlusion (1.0 = Blocks Light, 0.0 = Pass Through)

}