#version 330 core

// G-Buffer
uniform sampler2D u_occlusion; // Wall Map (Red channel > 0 = Wall)
uniform sampler2D u_normal;
uniform sampler2D u_albedo;    
uniform sampler2D u_depth;     // Depth Buffer

// Light Data
uniform vec3 u_light_pos;      // Real 3D Position (x, y, z)
uniform vec4 u_color;
uniform float u_radius;

// Camera Data
uniform mat4 u_matrix;         // View * Projection
uniform vec2 u_resolution;
uniform mat4 u_inv_matrix;     // Inverse View * Projection

in vec2 v_pos; // The 2D World Position of the Light Quad vertex

out vec4 f_color;

// --- UTILS ---
float interleaved_gradient_noise(vec2 pos) {
    vec3 magic = vec3(0.06711056, 0.00583715, 52.9829189);
    return fract(magic.z * fract(dot(pos, magic.xy)));
}

vec3 get_world_pos(vec2 uv) {
    float z_depth = texture(u_depth, uv).r;
    vec4 clip = vec4(uv * 2.0 - 1.0, z_depth * 2.0 - 1.0, 1.0);
    vec4 world = u_inv_matrix * clip;
    return world.xyz / world.w;
}

void main() {
    // 1. Current Pixel UV
    vec2 pixel_uv = gl_FragCoord.xy / u_resolution;

    // 2. Reconstruct REAL 3D Position of the surface
    vec3 pixel_pos_3d = get_world_pos(pixel_uv);

    // 3. Distance Check (True 3D Distance)
    float dist = distance(pixel_pos_3d, u_light_pos);
    if (dist > u_radius) discard;

    // --- RAYCASTING (SHADOWS) ---
    // We raycast from the Surface (pixel_pos_3d) to the Light (u_light_pos)
    
    // We only march in XY (Top-Down Shadow Map)
    // Vector from Pixel -> Light
    vec2 ray_dir = u_light_pos.xy - pixel_pos_3d.xy; 
    float ray_len = length(ray_dir);
    ray_dir = normalize(ray_dir);

    // Shadow Config
    float shadow = 1.0;
    int steps = 48; // Adjust for performance vs quality
    
    // Calculate step size
    // We don't need to check beyond the light, so limit max dist
    float step_size = min(ray_len, u_radius) / float(steps);

    // Jitter (Dithering to hide banding)
    float jitter = interleaved_gradient_noise(gl_FragCoord.xy);
    float current_dist = step_size * jitter; 

    // Accumulator for Soft Shadows
    float density = 0.0;

    for(int i = 0; i < steps; i++) {
        // Stop if we passed the light
        if (current_dist >= ray_len) break;

        // Move along the ray
        vec2 sample_world_pos = pixel_pos_3d.xy + (ray_dir * current_dist);
        
        // Project this World Point -> Screen UV to sample Occlusion Map
        // We use Z=0.0 because the occlusion map captures the "footprint" of walls
        vec4 screen_sample = u_matrix * vec4(sample_world_pos, 0.0, 1.0);
        vec2 sample_uv = (screen_sample.xy / screen_sample.w) * 0.5 + 0.5;

        // Check Bounds
        if (sample_uv.x >= 0.0 && sample_uv.x <= 1.0 && sample_uv.y >= 0.0 && sample_uv.y <= 1.0) {
            
            // Sample Wall Map
            float occ = texture(u_occlusion, sample_uv).r;
            
            if (occ > 0.0) {                
                // Soft Shadow Accumulation:
                density += occ * 3.0; // Higher multiplier = Harder shadows
                if (density >= 1.0) {
                    shadow = 0.0;
                    break;
                }
            }
        }
        current_dist += step_size;
    }
    
    // Apply accumulated density
    shadow = max(1.0 - density, 0.0);

    // --- LIGHTING ---
    
    // Falloff
    float falloff = pow(1.0 - (dist / u_radius), 2.0);

    // Albedo
    vec4 albedo = texture(u_albedo, pixel_uv);

    // Normals (3D Lighting)
    vec3 N = normalize(texture(u_normal, pixel_uv).rgb * 2.0 - 1.0);
    vec3 L = normalize(u_light_pos - pixel_pos_3d);
    
    float diffuse = max(dot(N, L), 0.0);

    // Special Case: Blue channel of normal map might indicate "Unlit" or "Flat" surface
    vec3 raw_normal = texture(u_normal, pixel_uv).rgb;
    if (raw_normal.b > 0.9) { 
       // diffuse = 1.0; // Optional: Force full brightness for some objects
    }

    float depth = texture(u_depth, pixel_uv).r;
    float aberration = smoothstep(0.1, 1.0, depth);
    aberration *= 0.001; // TUNE THIS (screen-space units)

    vec2 dir = normalize(pixel_uv - vec2(0.5));

    vec2 uv_r = clamp(pixel_uv + dir * aberration, 0.0, 1.0);
    vec2 uv_g = pixel_uv;
    vec2 uv_b = clamp(pixel_uv - dir * aberration, 0.0, 1.0);

    vec3 albedo_split;
    albedo_split.r = texture(u_albedo, uv_r).r;
    albedo_split.g = texture(u_albedo, uv_g).g;
    albedo_split.b = texture(u_albedo, uv_b).b;

    // --- FINAL COMBINE ---
    f_color = u_color * falloff * shadow * vec4(albedo_split, 1.0) * diffuse;
}