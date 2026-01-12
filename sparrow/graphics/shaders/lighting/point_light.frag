#version 460 core 

in vec2 v_uv;
out vec4 f_color;

layout(binding = 0) uniform sampler2D u_albedo;
layout(binding = 1) uniform sampler2D u_normal;
layout(binding = 2) uniform sampler2D u_depth;

uniform vec3 u_light_pos;
uniform vec4 u_color;
uniform float u_radius;

uniform mat4 u_inv_view_proj;
uniform mat4 u_view_proj;

// Voxel volume samplers (read-only)
layout(binding = 3) uniform sampler3D u_vox_albedoOcc; // rgb albedo, a occupancy
layout(binding = 4) uniform sampler3D u_vox_normal;    // xyz normal in [-1,1] stored as f16

// Voxel volume bounds in world space (camera centered)
uniform vec3 u_vox_min;
uniform vec3 u_vox_max;
uniform ivec3 u_vox_res;

// Shadow map (point light = cubemap)
layout(binding = 5) uniform sampler2D u_shadow_face0;
layout(binding = 6) uniform sampler2D u_shadow_face1;
layout(binding = 7) uniform sampler2D u_shadow_face2;
layout(binding = 8) uniform sampler2D u_shadow_face3;
layout(binding = 9) uniform sampler2D u_shadow_face4;
layout(binding = 10) uniform sampler2D u_shadow_face5;

// Shadow parameters
uniform float u_shadow_bias; // e.g. 0.05
uniform float u_shadow_far; // same as light radius or shadow pass far plane

// --- VCT SETTINGS ---
const int SHADOW_STEPS = 32; // Shadow raymarching steps
const int CONE_STEPS = 8; // GI steps per cone
const float GI_STRENGTH = 1.0; // Overall indirect multiplier
const float CONE_APERTURE = 0.35; // smaller = sharper, larger = blurrier
const float MAX_GI_DIST = 128.0; // World units; usually ~ light radius
const float OCC_ALPHA = 0.35; // How quickly cones become "blocked"

//  --- HELPERS ---

vec3 reconstruct_world_pos(vec2 uv, float depth) {
    vec4 clip = vec4(uv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
    vec4 world = u_inv_view_proj * clip;
    return world.xyz / world.w;
}

vec3 decodeNormal(vec3 enc) {
    return normalize(enc * 2.0 - 1.0);
}

bool worldToVox(vec3 w, out vec3 voxN) {
    voxN = (w - u_vox_min) / (u_vox_max - u_vox_min);
    return all(greaterThanEqual(voxN, vec3(0.0))) && all(lessThanEqual(voxN, vec3(1.0)));
}

float attenuation(float d, float r) {
    float x = max(1.0 - (d / r), 0.0);
    return x * x;
}

// Sample occupancy/albedo/normal from voxel volume
// uses mip LOD based on cone footprint size
// IMPORTANT: u_vox_albedoOcc must have mipmaps generated on CPU after voxelization.
vec4 sampleVoxAlbedoOcc(vec3 voxN, float lod) {
    return textureLod(u_vox_albedoOcc, voxN, lod);
}

vec3 sampleVoxNormal(vec3 voxN, float lod) {
    return textureLod(u_vox_normal, voxN, lod).xyz;
}

// Returns (faceIndex, uv) for a direction vector (from light to point)
void dirToFaceUV(vec3 d, out int face, out vec2 uv)
{
    vec3 ad = abs(d);

    if (ad.x >= ad.y && ad.x >= ad.z) {
        if (d.x > 0.0) { face = 0; uv = vec2(-d.z, -d.y) / ad.x; } // +X
        else           { face = 1; uv = vec2( d.z, -d.y) / ad.x; } // -X
    } else if (ad.y >= ad.x && ad.y >= ad.z) {
        if (d.y > 0.0) { face = 2; uv = vec2( d.x,  d.z) / ad.y; } // +Y
        else           { face = 3; uv = vec2( d.x, -d.z) / ad.y; } // -Y
    } else {
        if (d.z > 0.0) { face = 4; uv = vec2( d.x, -d.y) / ad.z; } // +Z
        else           { face = 5; uv = vec2(-d.x, -d.y) / ad.z; } // -Z
    }

    uv = uv * 0.5 + 0.5; // [-1,1] -> [0,1]
}

float sampleShadowMap(vec3 worldPos) {
    vec3 L = worldPos - u_light_pos;
    float currentDepth = length(L);

    int face;
    vec2 uv;
    dirToFaceUV(L, face, uv);

    float closestDepthN;
    if (face == 0) closestDepthN = texture(u_shadow_face0, uv).r;
    else if (face == 1) closestDepthN = texture(u_shadow_face1, uv).r;
    else if (face == 2) closestDepthN = texture(u_shadow_face2, uv).r;
    else if (face == 3) closestDepthN = texture(u_shadow_face3, uv).r;
    else if (face == 4) closestDepthN = texture(u_shadow_face4, uv).r;
    else closestDepthN = texture(u_shadow_face5, uv).r;

    float closestDepth = closestDepthN * u_shadow_far;
    return (currentDepth - u_shadow_bias) > closestDepth ? 0.0 : 1.0;
}


// ----------------------------------------------------------------------------
// 3D cone trace that evaluates *single-bounce from the current light only*.
// we do not store radiance in the voxels; we store material+occupancy+normal,
// then evaluate lighting at the hit samples.
// ----------------------------------------------------------------------------
vec3 traceConeGI(vec3 startW, vec3 dirW, float aperture, float maxDistW) {
    vec3 acc = vec3(0.0);
    float accAlpha = 0.0;
    
    // Start slightly offset to avoid hitting self
    float distW = 2.0;
    
    for(int i = 0; i < CONE_STEPS; i++) {
        vec3 sampleW = startW + dirW * distW;

        vec3 voxN;
        if(!worldToVox(sampleW, voxN)) break; // Out of bounds

        // Cone radius grows with distance; use that to pick mip LOD.
        // Convert cone radius from world units to "normalized voxel space" footprint.
        // worldSize per axis:
        vec3 worldSize = u_vox_max - u_vox_min;

        float coneRadiusW = distW * aperture;
        float footprintN = coneRadiusW / max(max(worldSize.x, worldSize.y), worldSize.z);

        // LOD from footprint relative to a single voxel
        // Voxel size (normalized) ~ 1 / maxRes
        float baseVox = 1.0 / float(max(u_vox_res.x, max(u_vox_res.y, u_vox_res.z)));
        float lod = clamp(log2(max(footprintN / baseVox, 1e-6)), 0.0, 8.0); // max 8 mip levels

        vec4 ao = sampleVoxAlbedoOcc(voxN, lod);
        float occ = ao.a;



        if (occ > 0.1) {
            // We "hit" some geometry in this cone.
            // Evaluate bounce from THIS light at this bounce point.
            vec3 nB = normalize(sampleVoxNormal(voxN, lod));
            // If u_vox_normal is rrgba16f storing [-1, 1], this is already correct.
            // If it were stored as u8 [0,255], we would need to decode:
            // vec3 nB = decodeNormal(sampleVoxNormal(voxN, lod));

            vec3 L = u_light_pos - sampleW;
            float d = length(L);
            
            if (d < u_radius) {
                vec3 ldir = L / max(d, 1e-6);

                float ndotl = max(dot(nB, ldir), 0.0);
                float att = attenuation(d, u_radius);

                // Simple lambert bounce:
                // bounceRadiance = albedo * lightColor * (ndotl * att)
                vec3 bounce = ao.rgb * u_color.rgb * (ndotl * att);
                
                // Accumulate with remaining transparency
                acc += bounce * (1.0 - accAlpha);
            }
            
            // Accumulate Opacity (Walls are solid, so we gain opacity fast)
            accAlpha += OCC_ALPHA;
            if (accAlpha > 0.95) break;
        }
        distW += max(coneRadiusW, 1.0);
        if (distW > maxDistW) break;
    }
    
    return acc;
}

mat3 makeTBN(vec3 n) {
    // Build a stable tangent basis for hemisphere cone directions
    vec3 up = abs(n.z) < 0.999 ? vec3(0.0, 0.0, 1.0) : vec3(0.0, 1.0, 0.0);
    vec3 t = normalize(cross(up, n));
    vec3 b = cross(n, t);
    return mat3(t, b, n);
}

void main() {
    float my_depth = texture(u_depth, v_uv).r;
    if (my_depth == 1.0) discard;

    vec3 world_pos = reconstruct_world_pos(v_uv, my_depth);


    //float d = texture(u_shadow_face0, vec2(0.5, 0.5)).r;
    //f_color = vec4(d, d, d, 1.0); // DEBUG: visualize shadow map depth
    //return;

    // Direct light range test
    float dL = distance(world_pos, u_light_pos);
    if (dL > u_radius) discard;

    // Read GBuffer normal (now real)
    vec3 n = decodeNormal(texture(u_normal, v_uv).xyz);
    vec3 ldir = normalize(u_light_pos - world_pos);

    float ndotl = max(dot(n, ldir), 0.0);
    float falloff = attenuation(dL, u_radius);

    // We can later replace this with
    // voxel-grid shadowing if desired.
    float shadow = sampleShadowMap(u_light_pos);

    vec3 direct = u_color.rgb * (ndotl * falloff * shadow);

    // Indirect (Voxel Cone Tracing in 3D)
    mat3 tbn = makeTBN(n);

    // Local hemisphere directions (z is up in tangent space)
    vec3 d0 = normalize(vec3( 0.0,  0.0, 1.0)); // Along normal
    vec3 d1 = normalize(vec3( 0.8,  0.0, 0.6));
    vec3 d2 = normalize(vec3(-0.8,  0.0, 0.6));
    vec3 d3 = normalize(vec3( 0.0,  0.8, 0.6));
    vec3 d4 = normalize(vec3( 0.0, -0.8, 0.6));

    float giMax = min(MAX_GI_DIST, u_radius);

    vec3 indirect = vec3(0.0);
    indirect += traceConeGI(world_pos, normalize(tbn * d0), CONE_APERTURE, giMax);
    indirect += traceConeGI(world_pos, normalize(tbn * d1), CONE_APERTURE, giMax);
    indirect += traceConeGI(world_pos, normalize(tbn * d2), CONE_APERTURE, giMax);
    indirect += traceConeGI(world_pos, normalize(tbn * d3), CONE_APERTURE, giMax);
    indirect += traceConeGI(world_pos, normalize(tbn * d4), CONE_APERTURE, giMax);

    indirect *= (GI_STRENGTH / 5.0);

    // IMPORTANT: Your composite shader multiplies albedo * lighting :contentReference[oaicite:6]{index=6}.
    // Therefore lighting here should represent "incoming light intensity/color",
    // and NOT be pre-multiplied by the surface albedo.
    //
    // Our indirect currently is bounceRadiance = bounceAlbedo * lightColor * ...
    // That is physically "light leaving the bounce surface", i.e. irradiance arriving at the shaded point.
    // In a full solution you’d transport that properly; here it’s a stylized single-bounce estimate.
    //
    // To keep your pipeline consistent, we treat (direct + indirect) as lighting to multiply by albedo.
    f_color = vec4(direct + indirect, 1.0);
}