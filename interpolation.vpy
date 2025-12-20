#!/usr/bin/env python3

"""
VapourSynth script for frame interpolation using MVTools or RIFE for mpv.

Copyright (C) 2025 github.com/president-not-sure
Licensed under GPLv2
"""

import json
import os
from typing import Any
import vapoursynth as vs
core = vs.core

FPS_PRECISION = 1e6

# Load shared libraries
home = os.path.expanduser("~")
lib_dir = os.path.join(home, ".local/lib/interpolation")
try:
    core.std.LoadPlugin(path=f"{lib_dir}/librife.so")
except (OSError, FileNotFoundError) as e:
    raise FileNotFoundError(
        f"'{lib_dir}/librife.so' missing. Did you forget to build the "
        "libraries? README.md for more info."
    ) from e
try:
    core.std.LoadPlugin(path=f"{lib_dir}/libmvtools.so")
except (OSError, FileNotFoundError) as e:
    raise FileNotFoundError(
        f"'{lib_dir}/libmvtools.so' missing. Did you forget to build the "
        "libraries? README.md for more info."
    ) from e


class UserData:
    """Holds validated user data."""
    __slots__ = [
        '_display_factor',
        '_fps_factor',
        '_library',
        '_rife_gpu_id'
    ]

    def __init__(self, user_data: str):
        # Default values for the user data
        self._set_display_factor("1.0")
        self._set_fps_factor("2.0")
        self._set_library("mvtools")
        self._set_rife_gpu_id(0)

        self._set_user_options(user_data)

    @property
    def display_factor(self) -> float:
        """
        Scaling factor applied to the display size to limit the video
        dimensions.
        """
        return self._display_factor

    def _set_display_factor(self, value: int | float | str):
        self._display_factor = validate_boundaries(
            value=value,
            label="display_factor",
            min=0.05,
            max=1.0
        )

    @property
    def fps_factor(self) -> float:
        """Frame rate multiplier."""
        return self._fps_factor

    def _set_fps_factor(self, value: int | float | str):
        self._fps_factor = validate_boundaries(
            value=value,
            label="fps_factor",
            min=1.0
        )

    @property
    def library(self) -> str:
        """Interpolation library."""
        return self._library

    def _set_library(self, value: str):
        valid_libraries = ('mvtools', 'rife')
        if value not in valid_libraries:
            raise ValueError(
                f"'{value}' is not a valid library. "
                f"Valid options are: {valid_libraries}."
            )
        self._library = value

    @property
    def rife_gpu_id(self) -> int:
        """ID of the GPU used by RIFE."""
        return self._rife_gpu_id

    def _set_rife_gpu_id(self, value: int | str):
        validate_type(value=value, expected_types=(int, str))
        validate_boundaries(value=value, label="rife_gpu_id", min=0)
        self._rife_gpu_id = int(value)

    def to_dict(self) -> dict:
        """Return a dictionary of all public properties."""
        d = {}
        for name in self.__slots__:
            name = name.lstrip('_')
            prop = getattr(self, name)
            if isinstance(prop, vs.VideoNode):
                d[name] = str(prop)
            else:
                d[name] = prop
        return d

    def __str__(self) -> str:
        """Return a string version of the object in JSON format."""
        return json.dumps(self.to_dict(), indent=4, sort_keys=True)

    def _set_user_options(self, value: str):
        """Parse and validate user_data"""
        if not isinstance(value, str):
            raise ValueError("user_data is not a string.")
        if value:
            pairs = value.split(",")
            for p in pairs:
                # Split each part by '=' to get the key-value pair
                if "=" not in p:
                    raise ValueError(
                        f"Invalid format for '{p}', expected key=value format."
                    )
                k, v = p.split("=", 1)
                k = f"_{k}"

                valid_options = self.__slots__
                if k not in valid_options:
                    raise ValueError(
                        f"'{k.lstrip('_')}' is not a valid option."
                    )
                else:
                    # Dynamically calls a set method by name with parameter
                    method = getattr(self, f"_set{k}")
                    method(v)


class MPVData:
    """Holds mpv-provided video information and validated user options."""
    __slots__ = [
        '_container_fps',
        '_display_fps',
        '_display_res',
        '_user_data',
        '_video_in',
        '_video_in_dh',
        '_video_in_dw'
    ]

    def __init__(
        self,
        container_fps: float,
        display_fps: float,
        display_res: list[int],
        user_data: str,
        video_in_dh: int,
        video_in_dw: int,
        video_in: vs.VideoNode
    ):
        """Initialize MPVData instance"""
        # mpv provided
        self._set_container_fps(container_fps)
        self._set_display_fps(display_fps)
        self._set_display_res(display_res)
        self._set_user_data(user_data)
        self._set_video_in(video_in)
        self._set_video_in_dh(video_in_dh)
        self._set_video_in_dw(video_in_dw)

    @property
    def container_fps(self) -> float:
        """FPS value as reported by file headers."""
        return self._container_fps

    def _set_container_fps(self, value: int | float | str):
        self._container_fps = validate_boundaries(
            value=value,
            label="container_fps",
            min=0,
            incl_min=False
        )

    @property
    def display_fps(self) -> float:
        """Refresh rate of the current display"""
        return self._display_fps

    def _set_display_fps(self, value: int | float | str):
        self._display_fps = validate_boundaries(
            value=value,
            label="display_fps",
            min=0,
            incl_min=False
        )

    @property
    def display_res(self) -> list[int]:
        """Resolution of the current display."""
        return self._display_res

    def _set_display_res(self, value: list[int]):
        self._display_res = validate_coord(value=value, label="display_res")

    @property
    def user_data(self) -> UserData:
        """User data passed from the filter."""
        return self._user_data

    def _set_user_data(self, value: str):
        if not isinstance(value, str):
            raise TypeError("user_data is not a string.")
        self._user_data = UserData(value)

    @property
    def video_in(self) -> vs.VideoNode:
        """The mpv video source as vapoursynth clip."""
        return self._video_in

    def _set_video_in(self, value: vs.VideoNode):
        if isinstance(value, vs.VideoNode):
            self._video_in = value
        else:
            raise TypeError(f"{type(value)} is not of type vs.VideoNode.")

    @property
    def video_in_dh(self) -> int:
        """Display height of the video."""
        return self._video_in_dh

    def _set_video_in_dh(self, value: int | float | str):
        validate_boundaries(value=value, label="video_in_dh", min=2)
        self._video_in_dh = int(value)

    @property
    def video_in_dw(self) -> int:
        """Display width of the video."""
        return self._video_in_dw

    def _set_video_in_dw(self, value: int | float | str):
        validate_boundaries(value=value, label="video_in_dh", min=2)
        self._video_in_dw = int(value)

    def to_dict(self) -> dict:
        """Return a dictionary of all public properties."""
        d = {}
        for name in self.__slots__:
            name = name.lstrip('_')
            prop = getattr(self, name)
            if not prop:
                d[name] = ""
            elif isinstance(prop, UserData):
                d[name] = prop.to_dict()
            elif isinstance(prop, vs.VideoNode):
                d[name] = str(prop)
            else:
                d[name] = prop
        return d

    def __str__(self) -> str:
        """Return a string version of the object in JSON format."""
        return json.dumps(self.to_dict(), indent=4, sort_keys=True)


def validate_type(value: Any, expected_types: Any) -> Any:
    """
    Validate that the input is the expected type.

    Parameters:
        value: The value to validate.
        expected_types: The expected type or a tuple of types.

    Returns:
        Any: The input value.

    Raises:
        TypeError: If the input is not the expected type.
    """
    if not isinstance(value, expected_types):
        raise TypeError(f"{type(value)} is not one of {expected_types}")

    return value


def validate_boundaries(
    value: int | float | str,
    label: str = "Value",
    min: int | float | None = None,
    incl_min: bool = True,
    max: int | float | None = None,
    incl_max: bool = True
) -> float:
    """
    Validate that a numeric value falls within boundaries.

    Parameters:
        value: The value to validate.
        label: Label for error messages.
        min: Minimum boundary.
        incl_min: Whether the min boundary is inclusive.
        max: Maximum boundary.
        incl_max: Whether the max boundary is inclusive.

    Returns:
        float: The input value cast into a float.

    Raises:
        ValueError: If the input is not a numeric type or within boundaries.
    """
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a numeric type")

    if min is not None:
        if incl_min:
            if value < min:
                raise ValueError(f"{label} must be >= {min}")
        else:
            if value <= min:
                raise ValueError(f"{label} must be > {min}")

    if max is not None:
        if incl_max:
            if value > max:
                raise ValueError(f"{label} must be <= {max}")
        else:
            if value >= max:
                raise ValueError(f"{label} must be < {max}")

    return value


def validate_coord(value: list[int], label: str = "Coordinate") -> list[int]:
    """
    Validate that the input is a coordinate.

    Parameters:
        value: The value to validate.
        label: Label for error messages.

    Returns:
        [int, int]: The input value.

    Raises:
        TypeError: If the input is not a list of 2 integers.
    """
    if (
        not isinstance(value, list)
        or not len(value) != 2
        or not all(isinstance(v, int) for v in value)
    ):
        raise TypeError(f"{label} must be a list of 2 integers.")

    return value


def make_even(number: float) -> int:
    """Round a number down to the nearest even integer."""
    return int(number) - int(number) % 2


def downscale(clip: vs.VideoNode, mpvd: MPVData):
    """
    Scale the video to fit within the display's resolution multiplied by
    user-provided display_factor. It never upscales the video.
    """
    display_width, display_height = mpvd.display_res

    # Calculate scaling factors to fit width and height within display
    scale_width = display_width * mpvd.user_data.display_factor / clip.width
    scale_height = display_height * mpvd.user_data.display_factor / clip.height

    # Choose the smaller scale to fit inside the display fill it
    scale = min(scale_width, scale_height)
    # Prevent upscaling
    scale = min(1, scale)

    # Scale dimensions and ensure compatibility
    target_width = make_even(clip.width * scale)
    target_height = make_even(clip.height * scale)

    # Only resize if scaling is necessary
    if scale < 1:
        return core.resize.Lanczos(
            clip=clip,
            width=target_width,
            height=target_height
        )
    else:
        return clip


def prepare_clip(mpvd: MPVData):
    """Downscale clip and set its frame rate."""
    clip = mpvd.video_in

    clip = downscale(clip=clip, mpvd=mpvd)

    fps_num = int(mpvd.container_fps * FPS_PRECISION)
    fps_den = int(FPS_PRECISION)
    clip = core.std.AssumeFPS(
        clip=clip,
        fpsnum=fps_num,
        fpsden=fps_den
    )

    return clip


def mvtools(mpvd: MPVData) -> vs.VideoNode:
    """Apply MVTools frame interpolation to a video clip."""
    clip = prepare_clip(mpvd)

    super = core.mv.Super(clip=clip)
    # Common parameters for motion vector analysis
    blksize = 32
    common_analyse_params = {
        'blksize': blksize,
        'overlap': int(blksize / 8),
        'truemotion': True
    }
    # Backward and forward motion vectors
    bwd_vec = core.mv.Analyse(
        super=super,
        isb=True,
        **common_analyse_params
    )
    fwd_vec = core.mv.Analyse(
        super=super,
        isb=False,
        **common_analyse_params
    )

    # Motion estimation and compensation.
    clip = core.mv.FlowFPS(
        clip=clip,
        super=super,
        mvbw=bwd_vec,
        mvfw=fwd_vec,
        num=int(clip.fps.numerator * mpvd.user_data.fps_factor),
        den=int(clip.fps.denominator),
        thscd1=200,
        thscd2=64
    )

    return clip


def rife(mpvd: MPVData) -> vs.VideoNode:
    """Apply RIFE frame interpolation to a video clip."""
    clip = prepare_clip(mpvd)

    super = core.mv.Super(clip=clip)
    # Common parameters for motion vector analysis
    blksize = 32
    common_analyse_params = {
        'blksize': blksize,
        'overlap': int(blksize / 8),
        'truemotion': True
    }
    # Backward motion vectors
    bwd_vec = core.mv.Analyse(
        super=super,
        isb=True,
        **common_analyse_params
    )

    # RIFE requires RGB 32bit input. Convert and restore after interpolation.
    original_format = clip.format.id
    clip = core.resize.Point(
        clip=clip,
        format=vs.RGBS,
        matrix_in=vs.MATRIX_BT709
    )

    # Only interpolate where needed
    clip = core.mv.SCDetection(
        clip=clip,
        vectors=bwd_vec,
        thscd1=200,
        thscd2=64
    )

    # AI assisted Real-Time Intermediate Flow Estimation
    clip = core.rife.RIFE(
        clip=clip,
        model=41,
        factor_num=int(mpvd.user_data.fps_factor * FPS_PRECISION),
        factor_den=int(FPS_PRECISION),
        gpu_id=mpvd.user_data.rife_gpu_id,
        gpu_thread=2,
        tta=False,
        uhd=True,
        sc=True,
        list_gpu=False
    )

    # Reset color space
    clip = core.resize.Point(
        clip=clip,
        format=original_format,
        matrix=vs.MATRIX_BT709
    )
    return clip


# Initialize the MPVData instance
mpvd = MPVData(
    container_fps=container_fps,  # noqa: F821
    display_fps=display_fps,  # noqa: F821
    display_res=display_res,  # noqa: F821
    user_data=user_data,  # noqa: F821
    video_in_dh=video_in_dh,  # noqa: F821
    video_in_dw=video_in_dw,  # noqa: F821
    video_in=video_in  # noqa: F821
)
# Output mpvd for debugging
print(f"\ninterpolation.vpy:\n{mpvd}")

# Start interpolation
if mpvd.user_data.library == "mvtools":
    clip = mvtools(mpvd)
elif mpvd.user_data.library == "rife":
    clip = rife(mpvd)

# Output the processed clip
clip.set_output()
