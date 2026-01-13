#version 460 core

in vec2 v_uv;
out vec4 o_color;

uniform sampler2D u_g_albedo;
uniform sampler2D u_g_normal;
uniform sampler2D u_g_orm;
uniform sampler2D u_g_depth;

uniform mat4 u_inv_view_proj;
uniform vec3 u_camera_pos;

const int MAX_LIGHTS = 64;
uniform int  u_light_count;
uniform vec4 u_light_pos_radius[MAX_LIGHTS];       // xyz = position_ws, w = radius
uniform vec4 u_light_color_intensity[MAX_LIGHTS];  // rgb = color, w = intensity

vec3 reconstruct_ws(vec2 uv, float depth01) {
    // depth01 is assumed in [0,1] (standard depth texture sampling result)
    // Convert to NDC
    vec4 ndc = vec4(uv * 2.0 - 1.0, depth01 * 2.0 - 1.0, 1.0);
    vec4 ws  = u_inv_view_proj * ndc;

    return ws.xyz / max(ws.w, 1e-6);
}

void main() {
    vec4 albedo = texture(u_g_albedo, v_uv);

    // If your gbuffer normal is stored as (n*0.5+0.5) in rgb:
    vec3 n_enc = texture(u_g_normal, v_uv).xyz;
    vec3 normal_ws = normalize(n_enc * 2.0 - 1.0);

    vec3 orm = texture(u_g_orm, v_uv).xyz;
    float ao = orm.r;

    float depth01 = texture(u_g_depth, v_uv).r;

    // If depth is 1.0, it is often "no geometry" (background)
    // You can early-out to black.
    if (depth01 >= 0.999999) {
        o_color = vec4(0.0, 0.0, 0.0, 1.0);
        return;
    }

    vec3 pos_ws = reconstruct_ws(v_uv, depth01);
    vec3 V = normalize(u_camera_pos - pos_ws); // Keep camera pos alive

    vec3 out_rgb = vec3(0.0);

    for (int i = 0; i < u_light_count; i++) {
        vec3 Lpos = u_light_pos_radius[i].xyz;
        float radius = u_light_pos_radius[i].w;

        vec3 toL = Lpos - pos_ws;
        float dist = length(toL);

        if (dist >= radius || dist <= 1e-6) {
            continue;
        }

        vec3 L = toL / dist;

        // Soft radius falloff
        float x = 1.0 - (dist / radius);
        float atten = x * x;

        float ndotl = max(dot(normal_ws, L), 0.0);

        vec3 light_rgb = u_light_color_intensity[i].rgb;
        float intensity = u_light_color_intensity[i].w;

        vec3 diffuse = albedo.rgb * light_rgb * (ndotl * intensity * atten);

        out_rgb += diffuse;
    }

    // Apply AO lightly (starter)
    out_rgb *= mix(1.0, ao, 0.75);

    o_color = vec4(out_rgb, 1.0) + vec4(V * 0.0000000001, 0.0);
}
