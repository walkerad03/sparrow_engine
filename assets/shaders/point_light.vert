#version 330 core

layout (location = 0) in vec2 in_vert; // Quad vertices (0..1)
layout (location = 1) in vec2 in_uv;

uniform mat4 u_matrix;
uniform vec3 u_pos;   // Light Center
uniform vec2 u_size;  // Light Diameter

out vec2 v_pos;       // Send World Pos to Fragment
out vec2 v_uv;        // Quad UV (0..1)

void main() {
    vec2 scaled = in_vert * u_size;
    vec2 world_pos = scaled + u_pos.xy;
    
    v_pos = world_pos;
    v_uv = in_uv;

    gl_Position = u_matrix * vec4(world_pos, 0.0, 1.0);
    gl_Position.z += in_uv.x * 0.000001;
}