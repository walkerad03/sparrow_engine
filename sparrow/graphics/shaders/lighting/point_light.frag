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
uniform mat4 u_view_proj; 

// --- VCT SETTINGS ---
// Adjust these to tune performance vs quality
const int GI_STEPS = 12;         // Fewer steps than shadows (GI is low freq)
const float GI_MAX_DIST = 0.2;   // How far light bounces (in Screen UV space)
const float GI_STR = 1.5;        // Artificial boost to make bounces visible
const float VOXEL_SIZE = 1.0 / 512.0; // Approx texel size for LOD calc

vec3 reconstruct_world_pos(vec2 uv, float depth) {
    vec4 clip = vec4(uv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
    vec4 world = u_inv_view_proj * clip;
    return world.xyz / world.w;
}

// ----------------------------------------------------------------------------
// VOXEL CONE TRACE FUNCTION
// ----------------------------------------------------------------------------
// Casts a cone into the 2D texture "voxel" representation.
// Returns the accumulated light color that bounces back.
vec3 traceCone(vec2 start_uv, vec2 dir, float aperture) {
    vec3 acc_color = vec3(0.0);
    float acc_alpha = 0.0;
    
    // Start slightly offset to avoid hitting self
    float dist = VOXEL_SIZE * 4.0;
    
    for(int i = 0; i < GI_STEPS; i++) {
        vec2 sample_pos = start_uv + dir * dist;
        
        // Bounds check
        if(sample_pos.x < 0.0 || sample_pos.x > 1.0 || sample_pos.y < 0.0 || sample_pos.y > 1.0) break;

        // 1. Calculate Cone Diameter & Mip Level (LOD)
        // The further we go, the wider the cone, the higher the mip level we sample.
        float cone_radius = dist * aperture;
        float lod = log2(cone_radius / VOXEL_SIZE);

        // 2. Sample Scene Depth (Geometry Check)
        float d = textureLod(u_depth, sample_pos, lod).r;

        // 3. Did we hit a wall? 
        // (Assuming "Wall" is closer than background/floor. Adjust 0.99 if needed)
        if (d < 0.99) {
            // We hit a voxel (wall)! 
            
            // A. Check if this wall is actually lit by the Main Light
            // We need the world position of the wall we just hit
            vec3 bounce_pos = reconstruct_world_pos(sample_pos, d);
            float light_dist = distance(bounce_pos, u_light_pos);

            if (light_dist < u_radius) {
                // B. Calculate Lighting at the Bounce Surface
                float bounce_atten = pow(max(1.0 - (light_dist / u_radius), 0.0), 2.0);
                
                // C. Sample Wall Color (Albedo)
                vec3 bounce_albedo = textureLod(u_albedo, sample_pos, lod).rgb;

                // D. Accumulate Incoming Light
                // (WallColor * LightColor * LightIntensity * RemainingTransparency)
                acc_color += bounce_albedo * u_color.rgb * bounce_atten * (1.0 - acc_alpha);
            }
            
            // Accumulate Opacity (Walls are solid, so we gain opacity fast)
            acc_alpha += 0.5; 
        }

        // Early exit if cone is fully blocked
        if (acc_alpha >= 0.95) break;

        // Step forward (step size proportional to cone radius for efficiency)
        dist += max(cone_radius, VOXEL_SIZE);
        
        if (dist > GI_MAX_DIST) break;
    }
    
    return acc_color;
}

void main() {
    float my_depth = texture(u_depth, v_uv).r;
    if (my_depth == 1.0) discard; // Don't light the void

    // --- STANDARD LIGHTING ---
    vec3 world_pos = reconstruct_world_pos(v_uv, my_depth);
    float dist = distance(world_pos, u_light_pos);
    if (dist > u_radius) discard;

    vec3 dir = normalize(u_light_pos - world_pos);
    float max_dist = dist;
    
    // Raymarching Shadows (Direct Light)
    int steps = 32; // Lowered slightly to save perf for GI
    float step_size = max_dist / float(steps);
    vec3 ray_pos = world_pos + dir * (step_size * 2.0);
    float shadow = 1.0;

    for(int i = 0; i < steps; i++) {
        ray_pos += dir * step_size;
        vec4 screen_pos = u_view_proj * vec4(ray_pos, 1.0);
        vec2 ndc = screen_pos.xy / screen_pos.w; 
        vec2 uv = ndc * 0.5 + 0.5;

        if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) continue;
        float occ_depth = texture(u_depth, uv).r;
        if (occ_depth < 0.99) { 
            shadow = 0.0;
            break; 
        }
    }

    float falloff = pow(max(1.0 - (dist / u_radius), 0.0), 2.0);
    vec3 direct_light = u_color.rgb * falloff * shadow;


    // --- DYNAMIC INDIRECT GI (VOXEL CONE TRACING) ---
    // Only calculate GI for lit pixels to save performance
    vec3 indirect_light = vec3(0.0);
    
    // Assuming a top-down game, we want to trace cones "outwards" across the floor
    // to find nearby walls that might bounce light onto us.
    // We trace 4 cones in cardinal directions.
    
    float aperture = 0.5; // ~30 degrees wide cones
    
    indirect_light += traceCone(v_uv, vec2( 1.0,  0.0), aperture); // East
    indirect_light += traceCone(v_uv, vec2(-1.0,  0.0), aperture); // West
    indirect_light += traceCone(v_uv, vec2( 0.0,  1.0), aperture); // North
    indirect_light += traceCone(v_uv, vec2( 0.0, -1.0), aperture); // South
    
    indirect_light *= GI_STR; // Boost intensity

    // --- COMBINE ---
    // Note: We do NOT multiply Direct Light by Albedo here (Composite pass does that).
    // BUT Indirect Light already includes Albedo (from the bounce), so it is added directly.
    
    f_color = vec4(direct_light + indirect_light, 1.0);
}