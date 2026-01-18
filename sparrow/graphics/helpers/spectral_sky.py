import numpy as np

# --- Physical Constants from skytracer (atmosphere.cxx) ---
R_PLANET = 6360e3
R_ATMOS = 6420e3
H_R = 8000.0  # Rayleigh scale height (approximate standard atmosphere)
H_M = 1200.0  # Mie scale height

# Updated from atmosphere.cxx: GuimeraAtmosphere constructor uses g=0.8
MIE_G = 0.8

# --- SPECTRAL CONSTANTS (Optimized for n=4) ---
# We use 4 wavelengths to approximate the full spectrum loop in render_rgb.py
WAVELENGTHS = np.array([680.0, 550.0, 440.0, 400.0])  # nm

# Rayleigh: Proportional to 1 / lambda^4
# Based on standard Bucholtz 1995 used in atmosphere.cxx
BETA_R_BASE = 8.4e-32 / ((WAVELENGTHS * 1e-9) ** 4)

# Ozone: Approximate absorption cross sections for our 4 wavelengths
# Derived from Gorshelev 2014 data used in atmosphere.cxx
BETA_O_BASE = np.array([0.650e-6, 1.881e-6, 0.085e-6, 0.010e-6])

# Mie: Generally independent of wavelength
BETA_M_BASE = 21e-6

# Optimized Matrix: Maps our 4 spectral samples to CIE XYZ
# This simulates the integration step in spectral_util.py
SPEC_TO_XYZ = np.array(
    [
        [0.456, 0.252, 0.181, 0.052],
        [0.198, 0.742, 0.058, 0.002],
        [0.000, 0.005, 0.881, 1.014],
    ]
)


def ray_sphere_intersect(orig, dir, radius):
    """Vectorized Ray-Sphere Intersection."""
    b = np.sum(orig * dir, axis=-1)
    c = np.sum(orig * orig, axis=-1) - radius**2
    delta = b * b - c
    mask = delta >= 0
    sqrt_delta = np.sqrt(np.maximum(0, delta))
    return np.maximum(0.0, -b - sqrt_delta), -b + sqrt_delta, mask


def get_ozone_density(height_m):
    """
    Matches GuimeraAtmosphere::get_ozone_height_distribution from atmosphere.cxx
    The reference uses a piecewise constant distribution based on altitude layers.
    """
    # Normalize height to match C++ logic (0 at ground)
    h = height_m

    # We use np.select for vectorized piecewise function (like a switch statement)
    conditions = [
        h <= 9000.0,
        h <= 18000.0,
        h <= 27000.0,
        h <= 36000.0,
        h <= 45000.0,
        h <= 54000.0,
    ]

    # Values from atmosphere.cxx (normalized by 210.0f)
    values = [
        9.0 / 210.0,
        14.0 / 210.0,
        111.0 / 210.0,
        64.0 / 210.0,
        6.0 / 210.0,
        6.0 / 210.0,
    ]

    # Default 0.0 if > 54km
    return np.select(conditions, values, default=0.0)


def xyz_to_srgb(xyz):
    """Linear XYZ to Linear sRGB conversion (matching spectral_util.py)."""
    # Matrix from spectral_util.py :: xyz_to_linear_srgb
    transform = np.array(
        [
            [3.2404542, -1.5371385, -0.4985314],
            [-0.9692660, 1.8760108, 0.0415560],
            [0.0556434, -0.2040259, 1.0572252],
        ]
    )
    return np.dot(xyz, transform.T)


def generate_spectral_sky_lut(
    width: int = 1024,
    height: int = 512,
    sun_elevation: float = 45.2,
    sun_rotation: float = 179.0,
    sun_size: float = 0.545,
    sun_intensity: float = 1.0,
    sun_radiance: float = 1.0e4,
    sun_softness_deg: float = 0.1,
    altitude: float = 148.0,
    air_density: float = 1.0,
    aerosol_density: float = 1.1,
    ozone_density: float = 1.0,
    num_samples: int = 32,
) -> bytes:
    # 1. Sun Direction
    elev_rad = np.radians(sun_elevation)
    rot_rad = np.radians(sun_rotation)
    sun_dir = np.array(
        [
            np.cos(elev_rad) * np.sin(rot_rad),
            np.sin(elev_rad),
            np.cos(elev_rad) * np.cos(rot_rad),
        ],
        dtype=np.float32,
    )

    # 2. View Directions (Equirectangular)
    u = np.linspace(0, 1, width, dtype=np.float32)
    v = np.linspace(0, 1, height, dtype=np.float32)
    uu, vv = np.meshgrid(u, v)
    theta = (vv - 0.5) * np.pi
    phi = (uu - 0.5) * 2 * np.pi
    view_dirs = np.stack(
        [np.cos(theta) * np.sin(phi), np.sin(theta), np.cos(theta) * np.cos(phi)],
        axis=-1,
    )

    # 3. Raymarching Setup
    cam_pos = np.array([0, R_PLANET + altitude, 0], dtype=np.float32)
    _, t1, _ = ray_sphere_intersect(cam_pos, view_dirs, R_ATMOS)
    step_size = t1 / num_samples

    # Scaled Coefficients
    beta_r = BETA_R_BASE * air_density
    beta_m = BETA_M_BASE * aerosol_density
    beta_o = BETA_O_BASE * ozone_density

    # Accumulator for 4 wavelengths
    total_l = np.zeros((*t1.shape, 4), dtype=np.float32)

    # Accumulators for view ray depth
    view_depth_r = np.zeros_like(t1)
    view_depth_m = np.zeros_like(t1)
    view_depth_o = np.zeros_like(t1)

    # 4. Raymarching Loop
    for i in range(num_samples):
        sample_dist = step_size * (i + 0.5)
        sample_pos = cam_pos + view_dirs * sample_dist[..., np.newaxis]
        h = np.linalg.norm(sample_pos, axis=-1) - R_PLANET

        # Densities
        hr = np.exp(-h / H_R)
        hm = np.exp(-h / H_M)
        ho = get_ozone_density(h)  # Updated to match skytracer piecewise function

        _, t1_sun, _ = ray_sphere_intersect(sample_pos, sun_dir, R_ATMOS)

        # Optical Depth
        tau = (
            beta_r * (hr[..., np.newaxis] * t1_sun[..., np.newaxis])
            + beta_m * (hm[..., np.newaxis] * t1_sun[..., np.newaxis])
            + beta_o * (ho[..., np.newaxis] * t1_sun[..., np.newaxis])
        )

        attenuation = np.exp(-tau)

        # Phase Functions
        mu = np.sum(view_dirs * sun_dir, axis=-1)
        phase_r = (3.0 / (16.0 * np.pi)) * (1.0 + mu**2)

        # Mie Phase (Henyey-Greenstein g=0.8 from skytracer)
        g = MIE_G
        phase_m = (
            (3.0 / (8.0 * np.pi))
            * ((1.0 - g**2) * (1.0 + mu**2))
            / ((2.0 + g**2) * (1.0 + g**2 - 2.0 * g * mu) ** 1.5)
        )

        view_depth_r += hr * step_size
        view_depth_m += hm * step_size
        view_depth_o += ho * step_size

        tau_view = (
            beta_r * view_depth_r[..., None]
            + beta_m * view_depth_m[..., None]
            + beta_o * view_depth_o[..., None]
        )

        attenuation_view = np.exp(-tau_view)

        # Scattering equation
        total_l += (
            attenuation
            * attenuation_view
            * hr[..., np.newaxis]
            * beta_r
            * phase_r[..., np.newaxis]
            * step_size[..., np.newaxis]
        )
        total_l += (
            attenuation
            * attenuation_view
            * hm[..., np.newaxis]
            * beta_m
            * phase_m[..., np.newaxis]
            * step_size[..., np.newaxis]
        )

    # 5. Conversion and Tonemapping
    xyz = np.dot(total_l, SPEC_TO_XYZ.T)
    lin_rgb = xyz_to_srgb(xyz)

    # Ground Mask
    lin_rgb[view_dirs[..., 1] < -0.01] = 0.0

    # Output
    alpha = np.ones((height, width, 1), dtype=np.float32)
    return np.concatenate([lin_rgb, alpha], axis=-1).astype("f4").tobytes()
