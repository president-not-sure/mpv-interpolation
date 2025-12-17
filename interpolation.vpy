#!/usr/bin/env python3

"""
VapourSynth script for frame interpolation using MVTools or RIFE for mpv.

Copyright (C) 2025 github.com/president-not-sure
Licensed under GPLv2
"""

import os
import vapoursynth as vs
core = vs.core

# Load shared libraries
home = os.path.expanduser("~")
libdir = f"{home}/.local/lib/interpolation"
core.std.LoadPlugin(path=f"{libdir}/librife.so")
core.std.LoadPlugin(path=f"{libdir}/libmvtools.so")

def extract_user_options(user_data: str) -> dict:
    """
    Parse user-provided options for library choice, FPS factor, and display factor.

    Parameters:
        user_data (str): String of comma-separated key=value pairs.

    Returns:
        dict: Parsed options with keys 'library', 'fps_factor', 'display_factor'.

    Raises:
        ValueError: If an invalid key or value is provided.
    """
    # Set default user options
    user_options = {
        'library': 'mvtools',
        'fps_factor': 2.0,
        'display_factor': 1.0
    }
    # Extract if not empty
    if user_data:
        # Split the string by commas
        variables = user_data.split(',')
        
        for var in variables:
            # Split each part by '=' to get the key-value pair
            if '=' not in var:
                raise ValueError(f"Invalid format for '{var}', expected key=value format.")

            key, value = var.split('=')

            # Convert value to float for fps_factor and display_factor
            if key in ["fps_factor", "display_factor"]:
                try:
                    value = float(value)
                except ValueError:
                    raise ValueError(f"'{value}' is not a valid number for {key}")

            match key:
                case "library":
                    if value not in ["mvtools", "rife"]:
                        raise ValueError(f"'{value}' is not a valid library. Valid options are 'mvtools' or 'rife'.")
                case "fps_factor":
                    if value < 1.0:
                        raise ValueError(f"fps_factor must be greater than or equal to 1.0")
                case "display_factor":
                    if not 0.1 <= value <= 1.0:
                        raise ValueError(f"display_factor must be between 0.1 and 1.0 inclusively")
                case _:
                    raise ValueError(f"'{key}' is not a valid option. Valid options are: 'library', 'fps_factor', 'display_factor'.")
            
            user_options[key] = value
    
    return user_options

def make_even(number: float) -> int:
    """
    Round a number down to the nearest even integer.

    Parameters:
        number (float): The input number.

    Returns:
        int: The largest even integer less than or equal to the input.
    """
    return int(number) - int(number) % 2



def downscale(
    clip: vs.VideoNode,
    display_res: tuple[int, int],
    display_factor: float = 1.0
) -> vs.VideoNode:
    """
    Scales the video to fit within the display resolution, downscaling it
    proportionally to the display size. It never upscales the video.

    Parameters:
        clip (vs.VideoNode):Input video clip.
        display_res (tuple[int,int]): Target display resolution (width, height).
        display_factor (float): Scaling factor between 0.1 and 1.0.

    Returns:
        vs.VideoNode: Downscaled clip.
    
    Raises:
        ValueError: If display_factor is outside the valid range.
    """
    
    display_width, display_height = display_res

    if not 0.1 <= display_factor <= 1.0:
        raise ValueError("Factor must be between 0.1 and 1.0")

    # Calculate scaling factors to fit width and height within display
    # considering the display_factor
    scale_width = display_width * display_factor / clip.width
    scale_height = display_height * display_factor / clip.height

    # Choose the smaller scale to fit inside the display fill it
    scale = min(scale_width, scale_height)
    # Prevent upsacaling
    scale = min(1, scale)

    # Scale dimensions and ensure compatibility
    target_width = make_even(clip.width * scale)
    target_height = make_even(clip.height * scale)

    # Only resize if scaling is necessary
    if scale < 1:
        return core.resize.Lanczos(
            clip = clip,
            width = target_width,
            height = target_height
        )
    else:
        return clip

def mvtools(
    video_in: vs.VideoNode,
    display_res: tuple[int, int],
    display_factor: float,
    container_fps: float,
    fps_factor: float
) -> vs.VideoNode:
    """
    Apply MVTools frame interpolation to a video clip.

    Parameters:
        video_in (vs.VideoNode): Input video clip.
        display_res (tuple[int,int]): Target display resolution.
        display_factor (float): Scaling factor for downscaling.
        container_fps (float): Original FPS of the video.
        fps_factor (float): Factor to multiply FPS for interpolation.

    Returns:
        vs.VideoNode: Interpolated clip.
    """
    clip = video_in

    clip = downscale(
        clip = clip,
        display_res = display_res,
        display_factor = display_factor
    )

    super = core.mv.Super(clip = clip)

    fps_num = int(container_fps * 1e6)
    fps_den = int(1e6)
    clip = core.std.AssumeFPS(
        clip = clip,
        fpsnum = fps_num,
        fpsden = fps_den
    )

    # Common parameters for motion vector analysis
    blksize = 32
    common_analyse_params = {
        'blksize': blksize,
        'overlap': int(blksize / 8),
        'truemotion': True
    }
    # Backward and forward motion vectors
    bwd_vec = core.mv.Analyse(
        super = super,
        isb = True,
        **common_analyse_params
    )
    fwd_vec = core.mv.Analyse(
        super = super,
        isb = False,
        **common_analyse_params
    )

    # Motion estimation and compensation.
    clip = core.mv.FlowFPS(
        clip = clip,
        super = super,
        mvbw = bwd_vec,
        mvfw = fwd_vec,
        num = int(fps_num * fps_factor),
        den = fps_den,
        thscd1 = 200,
        thscd2 = 64
    )
    
    return clip

def rife(
    video_in: vs.VideoNode,
    display_res: tuple[int, int],
    display_factor: float,
    container_fps: float,
    fps_factor: float
) -> vs.VideoNode:
    """
    Apply RIFE frame interpolation to a video clip.

    Parameters:
        video_in (vs.VideoNode): Input video clip.
        display_res (tuple[int,int]): Target display resolution.
        display_factor (float): Scaling factor for downscaling.
        container_fps (float): Original FPS of the video.
        fps_factor (float): Factor to multiply FPS for interpolation.

    Returns:
        vs.VideoNode: Interpolated clip.
    """
    clip = video_in

    clip = downscale(
        clip = clip,
        display_res = display_res,
        display_factor = display_factor
    )

    super = core.mv.Super(clip = clip)

    fps_num = int(container_fps * 1e6)
    fps_den = int(1e6)
    clip = core.std.AssumeFPS(
        clip = clip,
        fpsnum = fps_num,
        fpsden = fps_den
    )

    # Common parameters for motion vector analysis
    blksize = 32
    common_analyse_params = {
        'blksize': blksize,
        'overlap': int(blksize / 8),
        'truemotion': True
    }
    # Backward and forward motion vectors
    bwd_vec = core.mv.Analyse(
        super = super,
        isb = True,
        **common_analyse_params
    )

    # Rife only accepts RGB color space
    original_format = clip.format.id
    clip = core.resize.Point(
        clip = clip,
        format = vs.RGBS,
        matrix_in = vs.MATRIX_BT709
    )

    # Only interpolate where needed
    clip = core.mv.SCDetection(
        clip = clip,
        vectors = bwd_vec,
        thscd1 = 200,
        thscd2 = 64
    )

    # AI assisted Real-Time Intermediate Flow Estimation
    clip = core.rife.RIFE(
        clip = clip,
        model = 41,
        factor_num = int(fps_factor * 1e6),
        factor_den = int(1e6),
        gpu_id = 0,
        gpu_thread = 1,
        tta = False,
        uhd = True,
        sc = True,
        list_gpu = False
    )
    
    # Reset color space
    clip = core.resize.Point(
        clip = clip,
        format = original_format,
        matrix = vs.MATRIX_BT709
)
    return clip

user_options = extract_user_options(user_data = user_data)
match user_options['library']:
    case 'mvtools':
        clip = mvtools(
            video_in = video_in,
            display_res = display_res,
            display_factor = user_options['display_factor'],
            container_fps = container_fps,
            fps_factor = user_options['fps_factor']
        )
    case 'rife':
        clip = rife(
            video_in = video_in,
            display_res = display_res,
            display_factor = user_options['display_factor'],
            container_fps = container_fps,
            fps_factor = user_options['fps_factor']
        )

# Output the processed clip
clip.set_output()
