#version 330 core

// World Position from Vertex Shader
in vec2 v_pos; 
in vec2 v_uv;

// The G-Buffer
uniform sampler2D u_occlusion; // To check for walls
uniform sampler2D u_albedo;    // To light up the floor/walls

// Light Data
uniform vec2 u_light_pos;
uniform vec4 u_color;
uniform float u_radius;

// Camera Data (Needed to convert WorldPos -> ScreenUV)
uniform mat4 u_matrix;      
uniform vec2 u_resolution;

out vec4 f_color;

void main() {
    vec2 dummy = v_uv * 0.0001;

    // 1. Distance Check
    float dist = distance(v_pos, u_light_pos);
    if (dist > u_radius) discard;

    // 2. Raycasting (Shadows)
    vec2 dir = normalize(u_light_pos - v_pos);
    float max_dist = dist;
    
    // Quality Settings
    // Higher steps = cleaner shadows but slower
    int steps = 128; 
    float step_size = max_dist / float(steps);

    vec2 ray_pos = v_pos;
    float shadow = 1.0;

    for(int i = 0; i < steps; i++) {
        ray_pos += dir * step_size;
        
        // --- COORDINATE CONVERSION START ---
        // Project Ray World Pos -> Screen Space -> NDC -> UV
        vec4 screen_pos = u_matrix * vec4(ray_pos, 0.0, 1.0);
        vec2 ndc = screen_pos.xy / screen_pos.w; 
        vec2 uv = ndc * 0.5 + 0.5;
        // --- COORDINATE CONVERSION END ---

        // Sample Occlusion (Red Channel)
        // If > 0.1, it's a wall.
        float occ = texture(u_occlusion, uv).r;
        
        if (occ > 0.1) {
            shadow = 0.0;
            break; // Hit wall, stop checking
        }
    }

    // 3. Falloff (Quadratic looks best)
    float falloff = pow(1.0 - (dist / u_radius), 2.0);

    // 4. Sample the Albedo (Color of the floor/wall under this pixel)
    // We need the UV of the CURRENT pixel (v_pos)
    vec4 screen_pos_here = u_matrix * vec4(v_pos, 0.0, 1.0);
    vec2 uv_here = (screen_pos_here.xy / screen_pos_here.w) * 0.5 + 0.5;

    
    vec4 albedo = texture(u_albedo, uv_here);

    // 5. Combine
    // Final = LightColor * Intensity * Shadow * SurfaceColor
    f_color = (u_color * falloff * shadow * albedo) + vec4(dummy.x, dummy.y, 0.0, 0.0);
}