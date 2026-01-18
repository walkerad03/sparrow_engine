import math
from datetime import datetime, timezone

import numpy as np

# In meters
R_PLANET = 6360e3
R_ATMOS = 6420e3

# Rayleigh scattering coefficients
BETA_R = np.array([5.802e-6, 13.558e-6, 33.100e-6])  # RGB
H_R = 8000.0  # Scale height (meters)

# Mie scattering coefficients (Aerosols/Dust)
BETA_M = 21e-6
H_M = 1200.0  # Scale height
MIE_G = 0.76  # Directionality (forward scattering)

# Ozone
BETA_O = np.array([0.650e-6, 1.881e-6, 0.085e-6])
H_O_CENTER = 25000.0  # Ozone layer is concentrated at 25km up
H_O_WIDTH = 15000.0  # Width of the layer


def ray_sphere_intersect(orig, dir, radius):
    """
    Vectorized Ray-Sphere intersection.

    Assumes sphere is at (0,0,0). Returns distance to intersections (t0, t1).
    dir must be normalized.
    """
    b = np.sum(orig * dir, axis=-1)
    c = np.sum(orig * orig, axis=-1) - radius**2
    delta = b * b - c

    mask = delta >= 0
    sqrt_delta = np.sqrt(np.maximum(0, delta))

    t0 = -b - sqrt_delta
    t1 = -b + sqrt_delta

    t0 = np.maximum(0.0, t0)

    return t0, t1, mask


def get_density_at_height(height):
    """
    Returns density coefficients for Rayleigh, Mie, and Ozone at a given height.
    """
    # Rayleigh & Mie (Exponential decay)
    hr = np.exp(-height / H_R)
    hm = np.exp(-height / H_M)

    # Ozone (Tent/Gaussian distribution centered at 25km)
    # Simple triangular distribution approximation
    ho = np.maximum(0.0, 1.0 - np.abs(height - H_O_CENTER) / H_O_WIDTH)

    return hr, hm, ho


def get_sun_dir_from_datetime(
    dt: datetime, lat: float, long: float
) -> tuple[float, float, float]:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    n = (dt.timestamp() / 86400.0) - 10957.5

    L = (280.460 + 0.9856474 * n) % 360
    g = math.radians((357.528 + 0.9856003 * n) % 360)

    l_ecliptic = math.radians(L + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g))

    epsilon = math.radians(23.439 - 0.0000004 * n)

    x = math.cos(l_ecliptic)
    y = math.cos(epsilon) * math.sin(l_ecliptic)
    z = math.sin(epsilon) * math.sin(l_ecliptic)

    alpha = math.atan2(y, x)
    delta = math.asin(z)

    gmst_hours = (
        6.697375 + 0.0657098242 * n + dt.hour + (dt.minute / 60) + (dt.second / 3600)
    ) % 24
    gmst_rad = math.radians(gmst_hours * 15)

    lst_rad = gmst_rad + math.radians(long)

    H = lst_rad - alpha

    lat_rad = math.radians(lat)

    sin_elev = math.sin(lat_rad) * math.sin(delta) + math.cos(lat_rad) * math.cos(
        delta
    ) * math.cos(H)
    elev = math.asin(sin_elev)

    y_az = math.sin(H) * math.cos(delta)
    x_az = math.cos(lat_rad) * math.sin(delta) - math.sin(lat_rad) * math.cos(
        delta
    ) * math.cos(H)
    azimuth = math.atan2(y_az, x_az) + math.pi

    y_comp = math.sin(elev)
    h_comp = math.cos(elev)

    x_comp = h_comp * math.sin(azimuth)
    z_comp = h_comp * math.cos(azimuth)

    return (-x_comp, -y_comp, -z_comp)


def generate_nishita_sky_lut(
    width: int = 1024,
    height: int = 512,
    sun_dir: tuple[float, float, float] = (0.0, 1.0, 0.0),
    num_samples: int = 32,
) -> bytes:
    """
    Generate a raw float32 byte buffer of an Equirectangular Skybox.

    Args:
        width: Texture width.
        height: Texture height.
        sun_dir: Direction TOWARDS the sun (normalized).
        num_samples: Ray march steps (higher is slower but smoother).
    """
    u = np.linspace(0, 1, width, dtype=np.float32)
    v = np.linspace(0, 1, height, dtype=np.float32)
    uu, vv = np.meshgrid(u, v)

    theta = (vv - 0.5) * np.pi
    phi = (uu - 0.5) * 2 * np.pi

    dir_x = np.cos(theta) * np.sin(phi)
    dir_y = np.sin(theta)
    dir_z = np.cos(theta) * np.cos(phi)

    view_dirs = np.stack([dir_x, dir_y, dir_z], axis=-1)

    cam_pos = np.array([0, R_PLANET + 1500.0, 0], dtype=np.float32)
    sun_dir_np = np.array(sun_dir, dtype=np.float32)

    t0, t1, valid_mask = ray_sphere_intersect(cam_pos, view_dirs, R_ATMOS)

    ray_len = t1
    step_size = ray_len / num_samples

    optical_depth_r = np.zeros_like(t1)
    optical_depth_m = np.zeros_like(t1)
    optical_depth_o = np.zeros_like(t1)

    total_r = np.zeros((*t1.shape, 3), dtype=np.float32)
    total_m = np.zeros((*t1.shape, 3), dtype=np.float32)

    for i in range(num_samples):
        sample_dist = step_size * (i + 0.5)
        sample_pos = cam_pos + view_dirs * sample_dist[..., np.newaxis]

        sample_height = np.linalg.norm(sample_pos, axis=-1) - R_PLANET

        hr, hm, ho = get_density_at_height(sample_height)

        t0_l, t1_l, _ = ray_sphere_intersect(sample_pos, sun_dir_np, R_ATMOS)

        light_depth_r = hr * t1_l
        light_depth_m = hm * t1_l
        light_depth_o = ho * t1_l

        tau = (
            BETA_R * (optical_depth_r[..., np.newaxis] + light_depth_r[..., np.newaxis])
            + BETA_M
            * 1.1
            * (optical_depth_m[..., np.newaxis] + light_depth_m[..., np.newaxis])
            + BETA_O
            * (optical_depth_o[..., np.newaxis] + light_depth_o[..., np.newaxis])
        )

        attenuation = np.exp(-tau)
        total_r += attenuation * hr[..., np.newaxis] * step_size[..., np.newaxis]
        total_m += attenuation * hm[..., np.newaxis] * step_size[..., np.newaxis]

    mu = np.sum(view_dirs * sun_dir_np, axis=-1)

    phase_r = (3.0 / (16.0 * np.pi)) * (1.0 + mu**2)

    g = MIE_G
    phase_m = (
        (3.0 / (8.0 * np.pi))
        * ((1.0 - g**2) * (1.0 + mu**2))
        / ((2.0 + g**2) * (1.0 + g**2 - 2.0 * g * mu) ** 1.5)
    )

    lin_color = (
        total_r * BETA_R * phase_r[..., np.newaxis]
        + total_m * BETA_M * phase_m[..., np.newaxis]
    )

    ms_factor = 0.5 * (1.0 - np.exp(-optical_depth_r))
    lin_color += lin_color * ms_factor[..., np.newaxis]

    lin_color *= 1.0

    mask = view_dirs[..., 1] < -0.02
    lin_color[mask] = 0.0

    alpha = np.ones((height, width, 1), dtype=np.float32)
    final_img = np.concatenate([lin_color, alpha], axis=-1)

    return final_img.astype("f4").tobytes()
