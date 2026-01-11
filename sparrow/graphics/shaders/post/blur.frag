#version 330 core

in vec2 v_uv;
uniform sampler2D u_texture;
uniform vec2 u_direction; // (1.0, 0.0) or (0.0, 1.0)
uniform vec2 u_resolution;

out vec4 f_color;

void main() {
    // 9-Tap Gaussian Kernel weights
    float weights[5] = float[](0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);

    // Center pixel
    vec3 color = texture(u_texture, v_uv).rgb * weights[0];
    
    // Offset step size (1.0 / resolution)
    vec2 tex_offset = 1.0 / u_resolution; 
    
    // Sample neighbors
    for(int i = 1; i < 5; ++i) {
        vec2 offset = vec2(float(i)) * tex_offset * u_direction;
        color += texture(u_texture, v_uv + offset).rgb * weights[i];
        color += texture(u_texture, v_uv - offset).rgb * weights[i];
    }
    
    f_color = vec4(color, 1.0);
}