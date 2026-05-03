#version 460 core

uniform sampler2D u_color_tex;
uniform sampler2D u_depth_tex;

uniform mat4 u_inv_view_proj;
uniform vec3 u_camera_pos;

uniform vec3 u_ring_center;
uniform float u_ring_inner_radius;
uniform float u_ring_outer_radius;
uniform float u_ring_half_height;

uniform vec3 u_fog_color;
uniform float u_base_density;
uniform float u_time;

in vec2 v_uv;
out vec4 fragColor;

const float EPS = 1e-6;
const float INF = 1e20;

struct Interval {
    float a;
    float b;
    bool valid;
};

Interval make_invalid() {
    return Interval(0.0, 0.0, false);
}

Interval intersect_intervals(Interval x, Interval y) {
    if (!x.valid || !y.valid) {
        return make_invalid();
    }

    float a = max(x.a, y.a);
    float b = min(x.b, y.b);
    if (b <= a) {
        return make_invalid();
    }
    return Interval(a, b, true);
}

float interval_length(Interval x, float t_min, float t_max) {
    if (!x.valid) {
        return 0.0;
    }
    float a = max(x.a, t_min);
    float b = min(x.b, t_max);
    return max(0.0, b - a);
}

Interval intersect_radius(vec3 ro, vec3 rd, vec3 center, float radius) {
    vec2 oc = ro.xz - center.xz;
    vec2 dir = rd.xz;

    float A = dot(dir, dir);
    float C = dot(oc, oc) - (radius * radius);

    if (A < EPS) {
        if (C <= 0.0) {
            return Interval(-INF, INF, true);
        }
        return make_invalid();
    }

    float B = 2.0 * dot(oc, dir);
    float disc = (B * B) - (4.0 * A * C);
    if (disc < 0.0) {
        return make_invalid();
    }

    float root = sqrt(max(disc, 0.0));
    float inv = 0.5 / A;
    float t0 = (-B - root) * inv;
    float t1 = (-B + root) * inv;

    if (t1 <= t0) {
        return make_invalid();
    }
    return Interval(t0, t1, true);
}

Interval intersect_height(vec3 ro, vec3 rd, vec3 center, float half_height) {
    float y_min = center.y - half_height;
    float y_max = center.y + half_height;

    if (abs(rd.y) < EPS) {
        if (ro.y < y_min || ro.y > y_max) {
            return make_invalid();
        }
        return Interval(-INF, INF, true);
    }

    float t0 = (y_min - ro.y) / rd.y;
    float t1 = (y_max - ro.y) / rd.y;
    if (t0 > t1) {
        float tmp = t0;
        t0 = t1;
        t1 = tmp;
    }

    if (t1 <= t0) {
        return make_invalid();
    }
    return Interval(t0, t1, true);
}

Interval intersect_finite_cylinder(
    vec3 ro,
    vec3 rd,
    vec3 center,
    float radius,
    float half_height
) {
    Interval r = intersect_radius(ro, rd, center, radius);
    Interval h = intersect_height(ro, rd, center, half_height);
    return intersect_intervals(r, h);
}

vec3 reconstruct_world(vec2 uv, float depth) {
    vec4 clip = vec4((uv * 2.0) - 1.0, (depth * 2.0) - 1.0, 1.0);
    vec4 world = u_inv_view_proj * clip;
    return world.xyz / max(world.w, EPS);
}

void main() {
    vec3 src = texture(u_color_tex, v_uv).rgb;
    float depth = texture(u_depth_tex, v_uv).r;

    vec3 ro = u_camera_pos;
    vec3 far_ws = reconstruct_world(v_uv, 1.0);
    vec3 rd = normalize(far_ws - ro);

    float t_max;
    if (depth >= 0.999999) {
        t_max = length(far_ws - ro);
    } else {
        vec3 hit_ws = reconstruct_world(v_uv, depth);
        t_max = length(hit_ws - ro);
    }

    if (t_max <= EPS) {
        fragColor = vec4(src, 1.0);
        return;
    }

    Interval outer_seg = intersect_finite_cylinder(
        ro,
        rd,
        u_ring_center,
        u_ring_outer_radius,
        u_ring_half_height
    );

    float outer_len = interval_length(outer_seg, 0.0, t_max);
    if (outer_len <= EPS) {
        fragColor = vec4(src, 1.0);
        return;
    }

    Interval inner_seg = intersect_finite_cylinder(
        ro,
        rd,
        u_ring_center,
        u_ring_inner_radius,
        u_ring_half_height
    );
    Interval overlap = intersect_intervals(outer_seg, inner_seg);

    float hole_len = interval_length(overlap, 0.0, t_max);
    float path_len = max(0.0, outer_len - hole_len);
    if (path_len <= EPS) {
        fragColor = vec4(src, 1.0);
        return;
    }

    float t_mid = clamp((outer_seg.a + outer_seg.b) * 0.5, 0.0, t_max);
    vec3 p_mid = ro + (rd * t_mid);
    vec3 rel = p_mid - u_ring_center;

    float r = length(rel.xz);
    float ring_width = max(u_ring_outer_radius - u_ring_inner_radius, 0.001);
    float edge = max(0.25, ring_width * 0.10);

    float radial_in = smoothstep(u_ring_inner_radius, u_ring_inner_radius + edge, r);
    float radial_out = 1.0 - smoothstep(u_ring_outer_radius - edge, u_ring_outer_radius, r);
    float radial = radial_in * radial_out;

    float h = abs(rel.y);
    float vertical = 1.0 - smoothstep(u_ring_half_height * 0.5, u_ring_half_height, h);

    float angle = atan(rel.z, rel.x);
    float swirl = 0.88 + (0.12 * sin((angle * 8.0) + (r * 0.35) - (u_time * 0.15)));

    float density = u_base_density * radial * vertical * swirl;
    float fog_factor = 1.0 - exp(-density * path_len);

    vec3 out_color = mix(src, u_fog_color, clamp(fog_factor, 0.0, 1.0));
    fragColor = vec4(out_color, 1.0);
}
