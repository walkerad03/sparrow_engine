#version 330 core

// World Position from Vertex Shader
in vec2 v_pos; 
in vec2 v_uv;

// The G-Buffer
uniform sampler2D u_occlusion; // To check for walls
uniform sampler2D u_normal;
uniform sampler2D u_albedo;    // To light up the floor/walls

// Light Data
uniform vec3 u_light_pos;
uniform vec4 u_color;
uniform float u_radius;

// Camera Data
uniform mat4 u_matrix;      
uniform vec2 u_resolution;

out vec4 f_color;

float interleaved_gradient_noise(vec2 pos) {
    vec3 magic = vec3(0.06711056, 0.00583715, 52.9829189);
    return fract(magic.z * fract(dot(pos, magic.xy)));
}

void main() {
    vec2 dummy = v_uv * 0.0001;

    // 1. Distance Check
    float dist = distance(v_pos, u_light_pos.xy);
    if (dist > u_radius) discard;

    // 2. Raycasting (Shadows)
    vec2 dir = normalize(u_light_pos.xy - v_pos);
    float max_dist = dist;
    
    // Quality Settings
    // Higher steps = cleaner shadows but slower
    int steps = 64; 
    float step_size = max_dist / float(steps);

    float jitter = interleaved_gradient_noise(gl_FragCoord.xy);
    
    vec2 ray_pos = v_pos + (dir * step_size * jitter);
    float shadow = 1.0;
    float accumulated_density = 0.0;

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
        
        //if (occ > 0.1) {
         //   shadow = 0.0;
          //  break; // Hit wall, stop checking
        //}

        if (occ > 0.0) {
            accumulated_density += occ * 2.0; // * 2.0 for sharper walls, remove for foggy walls
            if (accumulated_density >= 1.0) {
                shadow = 0.0;
                break;
            }
        }
    }

    shadow = max(1.0 - accumulated_density, 0.0);

    // 3. Falloff (Quadratic looks best)
    float falloff = pow(1.0 - (dist / u_radius), 2.0);

    // 4. Sample the Albedo (Color of the floor/wall under this pixel)
    // We need the UV of the CURRENT pixel (v_pos)
    vec4 screen_pos_here = u_matrix * vec4(v_pos, 0.0, 1.0);
    vec2 uv_here = (screen_pos_here.xy / screen_pos_here.w) * 0.5 + 0.5;
    
    vec4 albedo = texture(u_albedo, uv_here);

    vec3 normal_data = texture(u_normal, uv_here).rgb;
    vec3 N = normalize(normal_data * 2.0 - 1.0);
    
    float light_height = u_light_pos.z;
    vec3 light_pos_3d = u_light_pos;
    vec3 pixel_pos_3d = vec3(v_pos, 0.0);

    vec4 screen_pos = u_matrix * vec4(v_pos, 0.0, 1.0);
    vec2 screen_uv = (screen_pos.xy / screen_pos.w) * 0.5 + 0.5;
    
    
    vec3 L = normalize(light_pos_3d - pixel_pos_3d);


    float diffuse = max(dot(N, L), 0.0);

    if (normal_data.b > 0.9) { 
        diffuse = 1.0; 
     }

    // 5. Combine
    // Final = LightColor * Intensity * Shadow * SurfaceColor
    f_color = (u_color * falloff * shadow * albedo * diffuse) + vec4(dummy.x, dummy.y, 0.0, 0.0);
}