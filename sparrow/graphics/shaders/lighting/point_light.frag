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
uniform mat4 u_view_proj; // <--- This matches 'u_matrix' from your old shader

vec3 reconstruct_world_pos(vec2 uv, float depth) {
    vec4 clip = vec4(uv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
    vec4 world = u_inv_view_proj * clip;
    return world.xyz / world.w;
}

void main() {
    float my_depth = texture(u_depth, v_uv).r;
    
    // 1. Reconstruct World Position of the pixel we are lighting
    vec3 world_pos = reconstruct_world_pos(v_uv, my_depth);

    // 2. Distance Check
    float dist = distance(world_pos, u_light_pos);
    if (dist > u_radius) discard;

    // 3. Raycasting (Shadows) - Adapted from your Old Shader
    vec3 dir = normalize(u_light_pos - world_pos);
    float max_dist = dist;
    
    int steps = 64; 
    float step_size = max_dist / float(steps);

    vec3 ray_pos = world_pos;
    float shadow = 1.0;
    
    // Offset slightly to avoid self-shadowing on the pixel itself
    ray_pos += dir * (step_size * 2.0);

    for(int i = 0; i < steps; i++) {
        ray_pos += dir * step_size;
        
        // --- COORDINATE CONVERSION (Your Old Logic) ---
        // Project Ray World Pos -> Screen Space -> NDC -> UV
        vec4 screen_pos = u_view_proj * vec4(ray_pos, 1.0);
        vec2 ndc = screen_pos.xy / screen_pos.w; 
        vec2 uv = ndc * 0.5 + 0.5;

        // Check bounds to prevent wrapping artifacts
        if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) continue;

        // --- OCCLUSION CHECK ---
        // We use Depth as Occlusion.
        // Assuming Floor is at Depth ~1.0 (or whatever you clear to).
        // Anything significantly closer (e.g. < 0.99) is a "Wall".
        float occ_depth = texture(u_depth, uv).r;
        
        // If the ray passes over something that is "tall" (low depth value)
        // relative to the floor, it blocks the light.
        if (occ_depth < 0.99) { 
            shadow = 0.0;
            break; 
        }
    }

    // 4. Falloff
    float falloff = pow(max(1.0 - (dist / u_radius), 0.0), 2.0);

    // 5. Combine (No Albedo multiplication here, that happens in Post Process)
    f_color = u_color * falloff * shadow;
}