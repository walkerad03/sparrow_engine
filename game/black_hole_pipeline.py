from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import moderngl
import numpy as np

from sparrow.graphics.graph import (
    FramebufferDesc,
    PassBuildInfo,
    PassExecutionContext,
    PassResourceUse,
    RenderPass,
    RenderServices,
    TextureDesc,
)
from sparrow.graphics.graph.builder import RenderGraphBuilder
from sparrow.graphics.passes.clear import ClearPass
from sparrow.graphics.passes.tonemap import TonemapPass
from sparrow.graphics.utils import create_fullscreen_triangle, pack_mat4
from sparrow.graphics.utils.ids import PassId, ResourceId
from sparrow.graphics.utils.uniforms import set_uniform

BH_MASS = 1.0
BH_SPIN = 0.99995
EVENT_HORIZON_RADIUS = BH_MASS + float(
    np.sqrt(BH_MASS * BH_MASS - BH_SPIN * BH_SPIN)
)
INNER_DISC_RADIUS = 1.25
OUTER_DISC_RADIUS = 18.0
DISC_PEAK_TEMP_K = 9800.0
CELESTIAL_SPHERE_RADIUS = 120.0

BLACK_HOLE_VERTEX_SHADER = """
#version 460 core

layout (location = 0) in vec2 in_pos;
out vec2 v_uv;

void main() {
    v_uv = in_pos * 0.5 + 0.5;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""

BLOOM_COMPOSITE_VERTEX_SHADER = """
#version 460 core

layout (location = 0) in vec2 in_pos;
out vec2 v_uv;

void main() {
    v_uv = in_pos * 0.5 + 0.5;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""

BLOOM_COMPOSITE_FRAGMENT_SHADER = """
#version 460 core

uniform sampler2D u_scene;
uniform vec2 u_texel_size;
uniform float u_threshold;
uniform float u_intensity;

in vec2 v_uv;
out vec4 fragColor;

float luminance(vec3 c) {
    return dot(c, vec3(0.2126, 0.7152, 0.0722));
}

vec3 bright_pass(vec3 c, float threshold) {
    float l = luminance(c);
    float w = smoothstep(threshold, threshold + 1.2, l);
    return c * w;
}

void main() {
    vec3 base = texture(u_scene, v_uv).rgb;

    vec3 bloom = vec3(0.0);
    float wsum = 0.0;

    vec2 taps[12] = vec2[](
        vec2(1.0, 0.0),
        vec2(-1.0, 0.0),
        vec2(0.0, 1.0),
        vec2(0.0, -1.0),
        vec2(2.0, 1.0),
        vec2(-2.0, 1.0),
        vec2(2.0, -1.0),
        vec2(-2.0, -1.0),
        vec2(4.0, 0.0),
        vec2(-4.0, 0.0),
        vec2(0.0, 4.0),
        vec2(0.0, -4.0)
    );

    float weights[12] = float[](
        0.12, 0.12, 0.12, 0.12,
        0.08, 0.08, 0.08, 0.08,
        0.05, 0.05, 0.05, 0.05
    );

    vec3 c0 = bright_pass(base, u_threshold);
    bloom += c0 * 0.14;
    wsum += 0.14;

    for (int i = 0; i < 12; i++) {
        vec2 uv = v_uv + taps[i] * u_texel_size * 1.9;
        vec3 s = texture(u_scene, uv).rgb;
        vec3 b = bright_pass(s, u_threshold);
        bloom += b * weights[i];
        wsum += weights[i];
    }

    bloom /= max(wsum, 1e-4);
    vec3 color = base + bloom * u_intensity;
    fragColor = vec4(max(color, 0.0), 1.0);
}
"""

BLACK_HOLE_FRAGMENT_SHADER = """
#version 460 core

const float PI = 3.14159265359;
const int MAX_STEPS = 960;
const float MAX_TEMP_PROFILE = 0.488;

uniform mat4 u_inv_view_proj;
uniform vec3 u_camera_pos;

uniform vec3 u_bh_center;
uniform float u_mass;
uniform float u_spin;
uniform float u_event_horizon;
uniform float u_disc_inner_radius;
uniform float u_disc_outer_radius;
uniform float u_disc_peak_temp_k;
uniform float u_escape_radius;

in vec2 v_uv;
out vec4 fragColor;

float hash12(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

vec2 hash22(vec2 p) {
    return vec2(
        hash12(p + vec2(17.13, 11.97)),
        hash12(p + vec2(41.71, 29.53))
    );
}

vec3 star_layer(vec2 uv, float scale, float threshold, float seed) {
    vec2 grid = uv * scale;
    vec2 cell = floor(grid);
    vec2 f = fract(grid) - 0.5;

    float presence = hash12(cell + vec2(seed, seed * 1.37));
    if (presence < threshold) {
        return vec3(0.0);
    }

    vec2 jitter = hash22(cell + vec2(seed * 2.17, seed * 0.91)) - 0.5;
    float d = length(f - jitter * 0.7);

    float sharpness = mix(45.0, 85.0, hash12(cell + vec2(seed * 3.11, 2.0)));
    float core = exp(-d * sharpness);
    float halo = exp(-d * 8.0) * 0.09;

    float brightness = (presence - threshold) / max(1.0 - threshold, 1e-4);
    brightness = pow(brightness, 2.2);

    float color_pick = hash12(cell + vec2(seed * 5.53, seed * 7.91));
    vec3 cool = vec3(0.67, 0.75, 1.0);
    vec3 warm = vec3(1.0, 0.84, 0.70);
    vec3 neutral = vec3(0.94, 0.95, 1.0);
    vec3 tint = mix(cool, warm, color_pick);
    tint = mix(tint, neutral, 0.42);

    return tint * (core + halo) * brightness * 1.55;
}

vec3 starfield(vec3 dir_world) {
    float lon = atan(dir_world.z, dir_world.x) / (2.0 * PI) + 0.5;
    float lat = asin(clamp(dir_world.y, -1.0, 1.0)) / PI + 0.5;
    vec2 uv = vec2(lon, lat);

    vec3 stars = vec3(0.0);
    stars += star_layer(uv, 420.0, 0.9958, 13.1);
    stars += star_layer(uv, 800.0, 0.9976, 29.7);
    stars += star_layer(uv, 1260.0, 0.9989, 41.4);
    return stars;
}

vec3 world_to_kerr(vec3 v) {
    // Rotate axes so Kerr spin axis (z) maps to world up (y).
    return vec3(v.x, v.z, v.y);
}

vec3 kerr_to_world(vec3 v) {
    return vec3(v.x, v.z, v.y);
}

void cart_to_bl(vec3 p, float a, out float r, out float theta, out float phi) {
    float rho2 = dot(p, p);
    float term = rho2 - a * a;
    float radical = sqrt(max(term * term + 4.0 * a * a * p.z * p.z, 0.0));
    r = sqrt(max(0.5 * (term + radical), 1e-8));
    theta = acos(clamp(p.z / max(r, 1e-8), -1.0, 1.0));
    phi = atan(p.y, p.x);
}

vec3 bl_to_cart(
    float r,
    float theta,
    float phi,
    float a
) {
    float rho = sqrt(r * r + a * a);
    float st = sin(theta);
    return vec3(
        rho * st * cos(phi),
        rho * st * sin(phi),
        r * cos(theta)
    );
}

vec3 bl_dir_to_cart(
    float r,
    float theta,
    float phi,
    float a,
    float dr,
    float dtheta,
    float dphi
) {
    float rho = sqrt(r * r + a * a);
    float st = sin(theta);
    float ct = cos(theta);
    float cp = cos(phi);
    float sp = sin(phi);
    float rrho = r / max(rho, 1e-8);

    vec3 dpr = vec3(rrho * st * cp, rrho * st * sp, ct);
    vec3 dpt = vec3(rho * ct * cp, rho * ct * sp, -r * st);
    vec3 dpp = vec3(-rho * st * sp, rho * st * cp, 0.0);
    return dpr * dr + dpt * dtheta + dpp * dphi;
}

void estimate_initial_derivatives(
    float r,
    float theta,
    float phi,
    float a,
    vec3 ray_cart,
    out float dr,
    out float dtheta,
    out float dphi
) {
    float rho = sqrt(r * r + a * a);
    float st = sin(theta);
    float ct = cos(theta);
    float cp = cos(phi);
    float sp = sin(phi);
    float rrho = r / max(rho, 1e-8);

    vec3 dpr = vec3(rrho * st * cp, rrho * st * sp, ct);
    vec3 dpt = vec3(rho * ct * cp, rho * ct * sp, -r * st);
    vec3 dpp = vec3(-rho * st * sp, rho * st * cp, 0.0);

    vec3 er = normalize(dpr);
    vec3 et = normalize(dpt);
    vec3 ep = normalize(dpp);

    dr = dot(ray_cart, er);
    dtheta = dot(ray_cart, et) / max(length(dpt), 1e-8);
    dphi = dot(ray_cart, ep) / max(length(dpp), 1e-8);
}

vec3 blackbody_rgb(float temp_k) {
    float t = max(temp_k, 1000.0) / 100.0;
    float r;
    float g;
    float b;

    if (t <= 66.0) {
        r = 1.0;
        g = clamp(0.3900815788 * log(t) - 0.6318414438, 0.0, 1.0);
        if (t <= 19.0) {
            b = 0.0;
        } else {
            b = clamp(0.5432067891 * log(t - 10.0) - 1.1962540891, 0.0, 1.0);
        }
    } else {
        r = clamp(1.2929361861 * pow(t - 60.0, -0.1332047592), 0.0, 1.0);
        g = clamp(1.1298908609 * pow(t - 60.0, -0.0755148492), 0.0, 1.0);
        b = 1.0;
    }

    return vec3(r, g, b);
}

float disc_temperature_k(float r) {
    float x = u_disc_inner_radius / max(r, u_disc_inner_radius + 1e-4);
    float profile = pow(x, 0.75) * pow(max(1.0 - sqrt(x), 0.0), 0.25);
    return u_disc_peak_temp_k * (profile / MAX_TEMP_PROFILE);
}

vec3 disc_emission(
    float r,
    float phi,
    vec3 ray_dir_cart
) {
    float omega = 1.0 / (pow(r, 1.5) + u_spin);
    float v = clamp(r * omega, 0.0, 0.92);

    vec3 tangent = normalize(vec3(-sin(phi), cos(phi), 0.0));
    float mu = clamp(dot(tangent, -ray_dir_cart), -0.999, 0.999);

    float gamma = inversesqrt(max(1.0 - v * v, 1e-5));
    float doppler = 1.0 / (gamma * (1.0 - v * mu));
    doppler = clamp(doppler, 0.2, 4.0);

    float grav = sqrt(
        max(1.0 - (2.0 * u_mass) / max(r, 1e-4) + (u_spin * u_spin) / max(r * r, 1e-4), 0.04)
    );
    float g_factor = doppler * grav;

    float temp_obs = max(900.0, disc_temperature_k(r) * g_factor);
    vec3 color = blackbody_rgb(temp_obs);

    float emissivity = pow(u_disc_inner_radius / r, 2.15);
    float intensity = emissivity * pow(max(g_factor, 0.0), 4.0);
    intensity *= smoothstep(u_disc_inner_radius, u_disc_inner_radius * 1.18, r);
    intensity *= smoothstep(u_disc_outer_radius, u_disc_outer_radius * 0.72, r);
    intensity *= 5.6;

    return color * intensity;
}

void main() {
    vec2 ndc = v_uv * 2.0 - 1.0;
    vec4 far_point = u_inv_view_proj * vec4(ndc, 1.0, 1.0);
    far_point /= far_point.w;

    vec3 ro_world = u_camera_pos - u_bh_center;
    vec3 rd_world = normalize(far_point.xyz - u_camera_pos);

    vec3 ro = world_to_kerr(ro_world);
    vec3 rd = normalize(world_to_kerr(rd_world));

    float r;
    float theta;
    float phi;
    cart_to_bl(ro, u_spin, r, theta, phi);

    float dr0;
    float dtheta0;
    float dphi0;
    estimate_initial_derivatives(r, theta, phi, u_spin, rd, dr0, dtheta0, dphi0);

    float E = 1.0;
    float sin_t = sin(theta);
    float cos_t = cos(theta);
    float sin2_t = max(sin_t * sin_t, 1e-6);

    float L = (r * r + u_spin * u_spin) * sin2_t * dphi0;
    float sigma0 = r * r + u_spin * u_spin * cos_t * cos_t;
    float Q = (sigma0 * dtheta0) * (sigma0 * dtheta0)
        - u_spin * u_spin * E * E * cos_t * cos_t
        + (L * L) * (cos_t * cos_t / sin2_t);
    Q = max(Q, 0.0);

    float sign_r = (dr0 >= 0.0) ? 1.0 : -1.0;
    float sign_theta = (dtheta0 >= 0.0) ? 1.0 : -1.0;

    vec3 color = vec3(0.0);
    float transmittance = 1.0;
    int disc_hits = 0;
    bool captured = false;
    bool escaped = false;
    float r_min = r;

    float drdl = 0.0;
    float dthdl = 0.0;
    float dphdl = 0.0;
    float impact0 = length(cross(ro, rd));

    for (int i = 0; i < MAX_STEPS; i++) {
        if (r <= u_event_horizon + 1e-3) {
            captured = true;
            break;
        }
        if (r >= u_escape_radius) {
            escaped = true;
            break;
        }

        float st = sin(theta);
        float ct = cos(theta);
        float st2 = max(st * st, 1e-6);
        float ct2 = ct * ct;

        float sigma = r * r + u_spin * u_spin * ct2;
        float delta = r * r - 2.0 * u_mass * r + u_spin * u_spin;
        delta = max(delta, 1e-6);

        float P = E * (r * r + u_spin * u_spin) - u_spin * L;
        float R = P * P - delta * (Q + (L - u_spin * E) * (L - u_spin * E));
        float Theta = Q + u_spin * u_spin * E * E * ct2 - L * L * (ct2 / st2);

        if (R < -1e-5 || Theta < -1e-5) {
            escaped = true;
            break;
        }

        if (R < 0.0) {
            sign_r = -sign_r;
            R = 0.0;
        }
        if (Theta < 0.0) {
            sign_theta = -sign_theta;
            Theta = 0.0;
        }

        drdl = sign_r * sqrt(max(R, 0.0)) / sigma;
        dthdl = sign_theta * sqrt(max(Theta, 0.0)) / sigma;
        dphdl = (u_spin * P / delta + (L / st2 - u_spin * E)) / sigma;

        float h = clamp(0.00055 + 0.010 * (r / u_escape_radius), 0.00030, 0.012);
        h *= mix(0.20, 1.0, clamp((r - u_event_horizon) / (10.0 * u_mass), 0.0, 1.0));

        float r_prev = r;
        float theta_prev = theta;
        float phi_prev = phi;
        float c_prev = cos(theta_prev);

        r += drdl * h;
        theta += dthdl * h;
        phi += dphdl * h;
        theta = clamp(theta, 1e-4, PI - 1e-4);
        r_min = min(r_min, r);

        if (any(isnan(vec3(r, theta, phi))) || any(isinf(vec3(r, theta, phi)))) {
            escaped = true;
            break;
        }

        float c_cur = cos(theta);
        if (c_prev * c_cur <= 0.0) {
            float t = abs(c_prev) / max(abs(c_prev) + abs(c_cur), 1e-6);
            float r_hit = mix(r_prev, r, t);
            float phi_hit = mix(phi_prev, phi, t);

            if (r_hit > u_disc_inner_radius && r_hit < u_disc_outer_radius) {
                vec3 ray_dir = normalize(
                    bl_dir_to_cart(
                        r_hit,
                        0.5 * PI,
                        phi_hit,
                        u_spin,
                        drdl,
                        dthdl,
                        dphdl
                    )
                );

                color += transmittance * disc_emission(r_hit, phi_hit, ray_dir);
                transmittance *= 0.62;
                disc_hits += 1;
            }
        }
    }

    if (captured && impact0 > 7.0 * u_mass) {
        // Reject numerically unstable far-field captures that appear as a ghost shadow.
        captured = false;
        escaped = true;
    }

    if (escaped) {
        vec3 exit_dir_kerr = normalize(
            bl_dir_to_cart(r, theta, phi, u_spin, drdl, dthdl, dphdl)
        );
        vec3 exit_dir_world = normalize(kerr_to_world(exit_dir_kerr));
        color += transmittance * starfield(exit_dir_world);
    }

    if (captured && disc_hits == 0) {
        color = vec3(0.0);
    }

    if (!captured) {
        float photon_orbit = 1.42 * u_mass;
        float ring_core = exp(
            -pow((r_min - photon_orbit) / max(0.09 * u_mass, 1e-4), 2.0)
        );
        float ring_wide = exp(
            -pow((r_min - photon_orbit) / max(0.24 * u_mass, 1e-4), 2.0)
        );
        float ring_halo = exp(
            -pow((r_min - photon_orbit) / max(0.62 * u_mass, 1e-4), 2.0)
        );
        float photon_ring = ring_core + ring_wide * 0.60 + ring_halo * 0.40;
        color += vec3(1.0, 0.72, 0.36) * photon_ring * 2.6;
    }

    fragColor = vec4(max(color, 0.0), 1.0);
}
"""


@dataclass
class BlackHolePass(RenderPass):
    target: Optional[ResourceId] = None

    _program: moderngl.Program | None = None
    _triangle_buffer: moderngl.Buffer | None = None
    _vao: moderngl.VertexArray | None = None

    def build(self) -> PassBuildInfo:
        writes = [PassResourceUse(self.target, "write")] if self.target else []
        return PassBuildInfo(pass_id=self.pass_id, reads=[], writes=writes)

    def on_compile(
        self, ctx: moderngl.Context, services: RenderServices
    ) -> None:
        self._program = ctx.program(
            vertex_shader=BLACK_HOLE_VERTEX_SHADER,
            fragment_shader=BLACK_HOLE_FRAGMENT_SHADER,
        )
        self._triangle_buffer = create_fullscreen_triangle(ctx)

    def on_destroy(self) -> None:
        if self._vao:
            self._vao.release()
            self._vao = None
        if self._triangle_buffer:
            self._triangle_buffer.release()
            self._triangle_buffer = None
        if self._program:
            self._program.release()
            self._program = None

    def execute(self, ctx: PassExecutionContext) -> None:
        if not self._program or not self._triangle_buffer:
            return

        if not self._vao:
            self._vao = ctx.gl.vertex_array(
                self._program,
                [(self._triangle_buffer, "2f", "in_pos")],
            )

        if self.target:
            ctx.graph_resources[self.target].use()
        else:
            ctx.gl.screen.use()

        ctx.gl.disable(
            moderngl.DEPTH_TEST | moderngl.CULL_FACE | moderngl.BLEND
        )

        inv_view_proj = np.linalg.inv(ctx.frame.camera.view_proj).astype("f4")

        set_uniform(
            self._program, "u_inv_view_proj", pack_mat4(inv_view_proj.T)
        )
        set_uniform(
            self._program,
            "u_camera_pos",
            tuple(float(v) for v in ctx.frame.camera.position),
        )
        set_uniform(self._program, "u_bh_center", (0.0, 0.0, 0.0))
        set_uniform(self._program, "u_mass", BH_MASS)
        set_uniform(self._program, "u_spin", BH_SPIN)
        set_uniform(self._program, "u_event_horizon", EVENT_HORIZON_RADIUS)
        set_uniform(self._program, "u_disc_inner_radius", INNER_DISC_RADIUS)
        set_uniform(self._program, "u_disc_outer_radius", OUTER_DISC_RADIUS)
        set_uniform(self._program, "u_disc_peak_temp_k", DISC_PEAK_TEMP_K)
        set_uniform(self._program, "u_escape_radius", CELESTIAL_SPHERE_RADIUS)

        self._vao.render(mode=moderngl.TRIANGLES)


@dataclass
class BloomCompositePass(RenderPass):
    source_texture: ResourceId
    target: Optional[ResourceId] = None

    _program: moderngl.Program | None = None
    _triangle_buffer: moderngl.Buffer | None = None
    _vao: moderngl.VertexArray | None = None

    def build(self) -> PassBuildInfo:
        reads = [PassResourceUse(self.source_texture, "read")]
        writes = [PassResourceUse(self.target, "write")] if self.target else []
        return PassBuildInfo(pass_id=self.pass_id, reads=reads, writes=writes)

    def on_compile(
        self, ctx: moderngl.Context, services: RenderServices
    ) -> None:
        self._program = ctx.program(
            vertex_shader=BLOOM_COMPOSITE_VERTEX_SHADER,
            fragment_shader=BLOOM_COMPOSITE_FRAGMENT_SHADER,
        )
        self._triangle_buffer = create_fullscreen_triangle(ctx)

    def on_destroy(self) -> None:
        if self._vao:
            self._vao.release()
            self._vao = None
        if self._triangle_buffer:
            self._triangle_buffer.release()
            self._triangle_buffer = None
        if self._program:
            self._program.release()
            self._program = None

    def execute(self, ctx: PassExecutionContext) -> None:
        if not self._program or not self._triangle_buffer:
            return

        if not self._vao:
            self._vao = ctx.gl.vertex_array(
                self._program,
                [(self._triangle_buffer, "2f", "in_pos")],
            )

        if self.target:
            ctx.graph_resources[self.target].use()
        else:
            ctx.gl.screen.use()

        ctx.gl.disable(
            moderngl.DEPTH_TEST | moderngl.CULL_FACE | moderngl.BLEND
        )

        source = ctx.graph_resources[self.source_texture]
        source.use(location=0)

        width = float(max(ctx.resolution[0], 1))
        height = float(max(ctx.resolution[1], 1))

        set_uniform(self._program, "u_scene", 0)
        set_uniform(self._program, "u_texel_size", (1.0 / width, 1.0 / height))
        set_uniform(self._program, "u_threshold", 0.95)
        set_uniform(self._program, "u_intensity", 2.35)

        self._vao.render(mode=moderngl.TRIANGLES)


def build_black_hole_pipeline(builder: RenderGraphBuilder) -> None:
    builder.define_texture(
        ResourceId("hdr_color"),
        desc=TextureDesc(
            components=4,
            dtype="f2",
        ),
    )

    builder.define_texture(
        ResourceId("bloomed_hdr"),
        desc=TextureDesc(
            components=4,
            dtype="f2",
        ),
    )

    builder.define_framebuffer(
        ResourceId("main_fbo"),
        FramebufferDesc(
            color_attachments=[ResourceId("hdr_color")],
            depth_attachment=None,
        ),
    )

    builder.define_framebuffer(
        ResourceId("bloom_fbo"),
        FramebufferDesc(
            color_attachments=[ResourceId("bloomed_hdr")],
            depth_attachment=None,
        ),
    )

    builder.add_pass(
        ClearPass(
            pass_id=PassId("clear"),
            target=ResourceId("main_fbo"),
            color=(0.0, 0.0, 0.0, 1.0),
        )
    )

    builder.add_pass(
        BlackHolePass(
            pass_id=PassId("black_hole"),
            target=ResourceId("main_fbo"),
        )
    )

    builder.add_pass(
        BloomCompositePass(
            pass_id=PassId("bloom_composite"),
            source_texture=ResourceId("hdr_color"),
            target=ResourceId("bloom_fbo"),
        )
    )

    builder.add_pass(
        TonemapPass(
            pass_id=PassId("tonemap"),
            input_texture=ResourceId("bloomed_hdr"),
            target=None,
        )
    )
