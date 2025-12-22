#!/usr/bin/env python3

"""
VapourSynth script for frame interpolation using MVTools or RIFE for mpv.

Copyright (C) 2025 github.com/president-not-sure
Licensed under GPLv2
"""

from __future__ import annotations
from fractions import Fraction

import json
import os
import vapoursynth as vs
core = vs.core


# Load shared libraries
home = os.path.expanduser("~")
lib_dir = os.path.join(home, ".local/lib/interpolation")
core.std.LoadPlugin(path=f"{lib_dir}/librife.so")
core.std.LoadPlugin(path=f"{lib_dir}/libmvtools.so")


class DictMixin:
    """Dict methods for objects."""
    def to_dict(self) -> dict:
        """Dict or self"""
        d = {}
        for name in dir(self):
            if name.startswith("_"):
                continue
            attr = getattr(type(self), name, None)
            if isinstance(attr, property):
                value = getattr(self, name)
                if isinstance(value, vs.VideoNode):
                    d[name] = str(value)
                # Recursively convert nested config objects
                elif hasattr(value, "to_dict"):
                    d[name] = value.to_dict()
                else:
                    d[name] = value
        return d

    def __str__(self) -> str:
        """Pretty JSON of self"""
        return json.dumps(self.to_dict(), indent=4, sort_keys=True)


class ConfigMixin:
    """Helper methods for configurations objects."""
    def to_bool(
        self,
        value: bool | int | str,
        label: str | None = None
    ) -> bool:
        """
        Convert a value to a boolean.
        """
        # Convert string or int to bool
        if isinstance(value, str):
            lowercase_value = value.lower()
            if lowercase_value in ("false", "no", "0"):
                return False
            elif lowercase_value in ("true", "yes", "1"):
                return True
            else:
                if label is not None:
                    raise ValueError(
                        f"'{label}': invalid boolean string '{value}'"
                    )
                else:
                    raise ValueError(f"Invalid boolean string '{value}'")
        else:
            return bool(value)

    def validate_boundaries(
        self,
        value: int | float | str,
        label: str = "Value",
        min: int | float | None = None,
        incl_min: bool = True,
        max: int | float | None = None,
        incl_max: bool = True
    ) -> float:
        """
        Validate that a numeric value falls within boundaries.
        """
        value = float(value)

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


class MPVData(DictMixin):
    """Holds mpv-provided video information and validated user options."""
    def __init__(
        self,
        name: str,
        container_fps: float,
        display_fps: float,
        display_res: list[int],
        user_data: str,
        video_in_dh: int,
        video_in_dw: int,
        video_in: vs.VideoNode,
    ):
        """Initialize MPVData instance"""
        # mpv-provided
        self._container_fps = container_fps
        self._display_fps = display_fps
        self._display_res = display_res
        self._video_in = video_in
        self._video_in_dh = video_in_dh
        self._video_in_dw = video_in_dw

        # Call last as it needs 'container_fps' and 'display_fps' initialized
        self._config = Config(self, user_data)

    @property
    def container_fps(self) -> float:
        """FPS value as reported by file headers."""
        return self._container_fps

    @property
    def display_fps(self) -> float:
        """Refresh rate of the current display."""
        return self._display_fps

    @property
    def display_res(self) -> list[int]:
        """Resolution of the current display."""
        return self._display_res

    @property
    def video_in(self) -> vs.VideoNode:
        """The mpv video source as vapoursynth clip."""
        return self._video_in

    @property
    def video_in_dh(self) -> int:
        """Display height of the video."""
        return self._video_in_dh

    @property
    def video_in_dw(self) -> int:
        """Display width of the video."""
        return self._video_in_dw

    @property
    def config(self) -> Config:
        """User configuration object."""
        return self._config


class Config(DictMixin, ConfigMixin):
    """Holds validated user configuration."""
    def __init__(self, parent: MPVData, user_data_str: str):
        self._mpv = parent

        # Default config values
        self.display_area_factor = 1.0
        self.library = "mvtools"

        self._mvtools = MVToolsConfig(self)
        self._rife = RIFEConfig(self)

        self._parse_user_data(user_data_str)

    @property
    def display_area_factor(self) -> float:
        """
        display area * display_area_factor = target scaling of the video
        """
        return self._display_factor

    @display_area_factor.setter
    def display_area_factor(self, value: int | float | str):
        self._display_factor = self.validate_boundaries(
            value,
            "display_area_factor",
            min=0.05,
            max=1.0
        )

    @property
    def library(self) -> str:
        """Interpolation library."""
        return self._library

    @library.setter
    def library(self, value: str):
        valid_libraries = ('mvtools', 'rife')
        if value not in valid_libraries:
            raise ValueError(
                f"'{value}' is not a valid library. "
                f"Valid libraries are: {valid_libraries}."
            )
        self._library = value

    @property
    def mvtools(self) -> MVToolsConfig:
        """MVTools configuration object."""
        return self._mvtools

    @property
    def rife(self) -> RIFEConfig:
        """RIFE configuration object."""
        return self._rife

    def _parse_user_data(self, user_data_str: str):
        """
        Parse mpv user_data and assign values via (possibly nested) properties.
        """
        if not user_data_str:
            return

        for pair in user_data_str.split(","):
            if "=" not in pair:
                raise ValueError(f"Expected 'key=value' format, got '{pair}'")

            key, value = pair.split("=", 1)
            path = key.split(".")

            obj = self
            for name in path[:-1]:
                attr = getattr(type(obj), name, None)
                if not isinstance(attr, property):
                    raise ValueError(f"'{name}' is not a valid option group")
                obj = getattr(obj, name)

            final = path[-1]
            prop = getattr(type(obj), final, None)
            if not isinstance(prop, property) or prop.fset is None:
                raise ValueError(f"'{key}' is not a valid or settable option")

            setattr(obj, final, value)


class MVToolsConfig(DictMixin):
    """Holds validated MVTools config."""
    def __init__(self, parent: Config):
        self._config = parent

        # Default values for the MVTools library
        self._target = Target(self, fps=self._config._mpv.display_fps)

    @property
    def target(self) -> Target:
        """Target object."""
        return self._target


class RIFEConfig(DictMixin, ConfigMixin):
    """Holds validated RIFE config."""
    def __init__(self, parent: Config):
        self._config = parent

        # Default values for the RIFE library
        self.gpu_id = 0
        self.gpu_thread = 2
        self.list_gpu = False
        self.model = 41
        self.sc = True
        self.tta = False
        self.uhd = True
        self._target = Target(self, factor=2)

    @property
    def target(self) -> Target:
        """Target object."""
        return self._target

    @property
    def gpu_id(self) -> int:
        """ID of the GPU used by RIFE."""
        return self._gpu_id

    @gpu_id.setter
    def gpu_id(self, value: int | str):
        self.validate_boundaries(value, "rife.gpu_id", min=0)
        self._gpu_id = int(value)

    @property
    def gpu_thread(self) -> int:
        """Number of GPU threads used."""
        return self._gpu_thread

    @gpu_thread.setter
    def gpu_thread(self, value: int | str):
        self.validate_boundaries(value, "rife.gpu_thread", min=1)
        self._gpu_thread = int(value)

    @property
    def list_gpu(self) -> bool:
        """List GPU ID without interpolation."""
        return self._list_gpu

    @list_gpu.setter
    def list_gpu(self, value: bool | str):
        self._list_gpu = self.to_bool(value, "rife.list_gpu")

    @property
    def model(self) -> int:
        """RIFE's model index in the models directory."""
        return self._model

    @model.setter
    def model(self, value: int | str):
        models_dir = os.path.join(lib_dir, "models")

        # Every model has a directory and an index starting from 0.
        # Get the total model count to get the higher model index boundary.
        model_index_count = 0
        for entry in os.scandir(models_dir):
            if entry.is_dir():
                model_index_count += 1
        if model_index_count > 0:
            last_model_index = model_index_count - 1
        else:
            raise FileNotFoundError(f"No models found in {models_dir}")

        self.validate_boundaries(
            value,
            "rife.model",
            min=0,
            max=last_model_index
        )
        self._model = int(value)

    @property
    def sc(self) -> bool:
        """
        Scene change detection, which prevents interpolation in areas with
        significant scene changes.
        """
        return self._sc

    @sc.setter
    def sc(self, value: bool | str):
        self._sc = self.to_bool(value, "rife.sc")

    @property
    def tta(self) -> bool:
        """TTA (Test-Time Augmentation) during interpolation."""
        return self._tta

    @tta.setter
    def tta(self, value: bool | str):
        self._tta = self.to_bool(value, "rife.tta")

    @property
    def uhd(self) -> bool:
        """Ultra High Definition mode for interpolation."""
        return self._uhd

    @uhd.setter
    def uhd(self, value: bool | str):
        self._uhd = self.to_bool(value, "rife.uhd")


class FrameRate(DictMixin):
    """FPS or factor container used by Target()"""
    def __init__(
        self,
        parent: Target,
        kind: str = "fps",
        value: int | float = 0,
        num: int = 0,
        den: int = 0
    ):
        self._target = parent
        self._kind = kind
        self._value = value
        self._num = num
        self._den = den

    @property
    def den(self) -> int:
        """Denominator"""
        return self._den

    @den.setter
    def den(self, value: int):
        self._den = value

    @property
    def num(self) -> int:
        """Numerator"""
        return self._num

    @num.setter
    def num(self, value: int):
        self._num = value

    @property
    def value(self) -> int | float:
        """Value"""
        return self._value

    @value.setter
    def value(self, value: int | float | str):
        if self._kind == "fps":
            self._target._set_fps(float(value))
        elif self._kind == "factor":
            self._target._set_factor(int(value))
        else:
            raise ValueError(
                f"'target.FrameRate().value' expect 'fps' or 'factor', but "
                f"got '{value}'"
            )


class Target(DictMixin):
    """Target FPS and target factor."""
    MAX_DEN = int(1e6)

    def __init__(
        self,
        parent: MVToolsConfig | RIFEConfig,
        fps: int | float | str = 0,
        factor: int | str = 0
    ):
        self._parent = parent

        # Initialize values
        fps = float(fps)
        factor = int(factor)

        if fps == 0 and factor == 0:
            raise ValueError(
                "'target.fps.value' and 'target.factor.value' are empty"
            )
        elif fps != 0 and factor != 0:
            raise ValueError(
                "'target.fps.value' or 'target.factor.value' are "
                "mutually exclusive"
            )
        elif fps != 0:
            self._set_fps(fps)
        else:
            self._set_factor(factor)

    @property
    def fps(self) -> FrameRate:
        """FrameRate object."""
        return self._fps

    @fps.setter
    def fps(self, value: FrameRate):
        self._fps = value

    @property
    def factor(self) -> FrameRate:
        """FrameRate object."""
        return self._factor

    @factor.setter
    def factor(self, value: FrameRate):
        self._factor = value

    # Methods that manipulate fps and factor
    def _set_fps(self, fps: float):
        """Set fps and update factor accordingly."""
        video_fps = self._parent._config._mpv.container_fps
        display_fps = self._parent._config._mpv.display_fps

        if fps < video_fps:
            fps = video_fps
            print(
                "\nWarning: fps < video fps. Clamping to video fps "
                f"({video_fps})."
            )
        if fps > display_fps:
            fps = display_fps
            print(
                "\nWarning: fps > display fps. Clamping to display fps "
                f"({display_fps})."
            )

        # Replace fps FrameRate object factor fps
        num, den = self.fraction(fps)
        self.fps = FrameRate(self, "fps", value=fps, num=num, den=den)

        # Replace factor FrameRate object factor
        factor = fps / video_fps
        num, den = self.fraction(factor)
        self.factor = FrameRate(self, "factor", value=factor, den=den, num=num)

    def _set_factor(self, factor: int):
        """Set factor and update fps accordingly."""
        video_fps = int(self._parent._config._mpv.container_fps)
        display_fps = self._parent._config._mpv.display_fps

        if factor < 1:
            factor = 1
            print("\nWarning: factor < 1. Clamping to 1.")
        if factor * video_fps > display_fps:
            # Calculate the maximum possible int factor as a float
            max_factor = display_fps / video_fps
            factor = int(max_factor - (max_factor % 1))
            print(
                "\nWarning: factor * video fps > display fps. Clamping to "
                f"the highest integer factor ({factor}) that the display "
                "allows."
            )

        # Replace factor FrameRate object
        num = factor
        den = 1
        self.factor = FrameRate(self, "factor", value=factor, num=num, den=den)

        # Replace fps FrameRate object
        fps = factor * video_fps
        num, den = self.fraction(fps)
        self.fps = FrameRate(self, "fps", value=fps, den=den, num=num)

    @staticmethod
    def fraction(value: float) -> tuple[int, int]:
        f = Fraction(value).limit_denominator(Target.MAX_DEN)
        return f.numerator, f.denominator


def make_even(number: float) -> int:
    """Round a number down to the nearest even integer."""
    return int(number) - int(number) % 2


def downscale(clip: vs.VideoNode, mpvd: MPVData):
    """
    display area * display_area_factor = target scaling of the video

    Notes:
        - Ensures a predictable processing load for any video aspect ratio, as
          long as the video area, display area, and display_area_factor remain
          constant.
        - The video resolution will never be upscaled.
    """
    display_width, display_height = mpvd.display_res

    # Calculate the target display area taking display_area_factor into account
    target_area = (
        display_width
        * display_height
        * mpvd.config.display_area_factor
    )

    # Calculate the video area
    video_area = clip.width * clip.height

    # Calculate the scaling factor based on area ratio
    scale = (target_area / video_area) ** 0.5

    # Prevent upscaling beyond the original video dimensions
    scale = min(1, scale)

    # Calculate target dimensions and ensure even numbers
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

    # Convert 'container_fps' to integer fraction
    fps_num, fps_den = Target.fraction(mpvd.container_fps)

    clip = core.std.AssumeFPS(clip=clip, fpsnum=fps_num, fpsden=fps_den)

    return clip


def mvtools(mpvd: MPVData) -> vs.VideoNode:
    """Apply MVTools frame interpolation to a video clip."""
    mvtools = mpvd.config.mvtools

    clip = prepare_clip(mpvd)

    super_clip = core.mv.Super(clip=clip)
    # Common parameters for motion vector analysis
    blksize = 32
    common_params = {
        'blksize': blksize,
        'overlap': int(blksize / 8),
        'truemotion': True
    }
    # Backward and forward motion vectors
    bwd_vec = core.mv.Analyse(super=super_clip, isb=True, **common_params)
    fwd_vec = core.mv.Analyse(super=super_clip, isb=False, **common_params)

    # Motion estimation and compensation.
    clip = core.mv.FlowFPS(
        clip=clip,
        super=super_clip,
        mvbw=bwd_vec,
        mvfw=fwd_vec,
        num=mvtools.target.fps.num,
        den=mvtools.target.fps.den,
        thscd1=200,
        thscd2=64
    )

    return clip


def rife(mpvd: MPVData) -> vs.VideoNode:
    """Apply RIFE frame interpolation to a video clip."""
    rife = mpvd.config.rife

    clip = prepare_clip(mpvd)

    if mpvd.config.rife.sc:
        super_clip = core.mv.Super(clip=clip)

        # Backward motion vectors
        blksize = 32
        bwd_vec = core.mv.Analyse(
            super=super_clip,
            isb=True,
            blksize=blksize,
            overlap=int(blksize / 8),
            truemotion=True
        )

        # Only interpolate where needed
        clip = core.mv.SCDetection(
            clip=clip,
            vectors=bwd_vec,
            thscd1=200,
            thscd2=64
        )

    # RIFE requires RGB 32bit input. Convert and restore after interpolation.
    original_format = clip.format.id
    clip = core.resize.Point(
        clip=clip,
        format=vs.RGBS,
        matrix_in=vs.MATRIX_BT709
    )

    # AI assisted Real-Time Intermediate Flow Estimation
    clip = core.rife.RIFE(
        clip=clip,
        model=rife.model,
        factor_num=rife.target.factor.num,
        factor_den=rife.target.factor.den,
        gpu_id=rife.gpu_id,
        gpu_thread=rife.gpu_thread,
        tta=rife.tta,
        uhd=rife.uhd,
        sc=rife.sc,
        list_gpu=rife.list_gpu
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
    name="mpvd",
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
if mpvd.config.library == "mvtools":
    clip = mvtools(mpvd)
elif mpvd.config.library == "rife":
    clip = rife(mpvd)

# Output the processed clip
clip.set_output()
