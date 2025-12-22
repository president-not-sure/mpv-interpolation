# mpv-interpolation

A **VapourSynth** script for frame interpolation, allowing smooth motion and frame rate conversion using **MVTools** or **RIFE** in **mpv**.

- [**VapourSynth**](https://www.vapoursynth.com/) is an application for video manipulation.
- [**MVTools**](https://github.com/dubhater/vapoursynth-mvtools) is a set of filters for motion estimation and compensation.
  - A CPU based algorithm that is less demanding and allows for better resolution at the cost of some artifacts.
  - A laptop can run it easily.
  - Very good for anime.
- [**RIFE**](https://github.com/styler00dollar/VapourSynth-RIFE-ncnn-Vulkan.git) is a Real-Time Intermediate Flow Estimation for Video Frame Interpolation, based on rife-ncnn-vulkan.
  - It is AI assisted and heavily dependent on a powerful GPU but gives the best results.
- [**mpv**](https://mpv.io/) is a free (as in freedom) media player for the command line. It supports a wide variety of media file formats, audio and video codecs, and subtitle types.

## Requirements

- Linux
- Podman
- mpv (Flatpak or baremetal)
- An internet connection
- GPU drivers and multimedia codecs should preferably be installed

## Build MVTools and RIFE libraries and download RIFE models

This will compile the required libraries and place them in `${HOME}/.local/lib/interpolation`. Once the compilation is complete, the image can be safely discarded as it is no longer needed.

```sh
# Add `--no-cache` to force a new build.
podman build \
    --tag=localhost/mpv-interpolation:latest \
    --file=Dockerfile \
    --output="${HOME}/.local/lib/interpolation"
```

## Install the interpolation script

### Non-Flatpak users

```sh
mpv_config_dir="${HOME}/.config/mpv/vapoursynth"
mkdir -p "$mpv_config_dir"
cp -afv interpolation.vpy "$mpv_config_dir"
```

### Flatpak mpv users

```sh
mpv_config_dir="${HOME}/.var/app/io.mpv.Mpv/config/mpv/vapoursynth"
mkdir -p "$mpv_config_dir"
cp -afv interpolation.vpy "$mpv_config_dir"
```

## Usage

Options are passed to the VapourSynth script via mpv's key bindings. These key bindings use the user-data key, whose value is a string of key–value pairs. Each key–value pair is written as `key=value`, and multiple pairs are separated by `,`. Option order does not matter. Omitted key-values pairs will be set to default values. Specifying the path of the script is the minimal configuration.

### display_area_factor

- description: display area * display_area_factor = target scaling of the video
- notes:
  - Ensures a predictable processing load for any video aspect ratio, as long as the video area, display area, and display_area_factor remain constant.
  - The video resolution will never be upscaled.
- constraints: Between 0.05 and 1.0 inclusively.
- default: 1.0
- type: float

### library

- description: Interpolation library.
- constraints: mvtools, rife
- default: mvtools
- type: str

### rife.gpu_id

- description: ID of the GPU used by RIFE.
- constraints: Greater or equal to 0.
- default: 0
- type: int

### rife.gpu_thread

- description: Number of GPU threads used by RIFE.
- constraints: Greater or equal to 1.
- default: 2
- type: int

### rife.list_gpu

- description: List available GPU IDs without performing interpolation.
- constraints: true or false
- default: false
- type: bool

### rife.model

- description: RIFE's model index in the models directory.
- constraints: Between 0 and the total number of available models minus 1.
- default: 41
- type: int

### rife.sc

- description: Scene change detection, which prevents interpolation in areas with significant scene changes.
- constraints: true or false
- default: true
- type: bool

### rife.tta

- description: TTA (Test-Time Augmentation) during interpolation.
- constraints: true or false
- default: false
- type: bool

### rife.uhd

- description: Ultra High Definition mode for interpolation.
- constraints: true or false
- default: true
- type: bool

### rife.target.fps.value

- description: Target frame rate for RIFE interpolation. Mutually exclusive with factor.
- constraints: Between the video FPS and the display FPS.
- note: Clamped to constraints.
- default: Display FPS.
- type: float

### rife.target.int_factor.value

- description: Integer factor by which to multiply the original frame rate for RIFE interpolation. Mutually exclusive with fps.
- constraints: Between 1 and the highest integer factor that the display will allow.
- note: Clamped to constraints.
- default: 2
- type: int

### mvtools.target.fps.value

- description: Target frame rate for MVTools interpolation. Mutually exclusive with factor.
- constraints: Between the video FPS and the display FPS.
- note: Clamped to constraints.
- default: Display FPS.
- type: float

### mvtools.target.int_factor.value

- description: Integer factor by which to multiply the original frame rate for MVTools interpolation. Mutually exclusive with fps.
- constraints: Greater or equal to 1 or the highest integer factor that the display will allow.
- note: Clamped to constraints.
- default: 2
- type: int

### Examples

Add the following in your `~/.config/mpv/input.conf` or `/.var/app/io.mpv.Mpv/config/mpv/input.conf` for Flatpak users. `~~home/` is mpv's config directory.

```conf
ctrl+i vf toggle vapoursynth=file=~~home/vapoursynth/interpolation.vpy:user-data="library=mvtools"
ctrl+I vf toggle vapoursynth=file=~~home/vapoursynth/interpolation.vpy:user-data="library=rife,display_area_factor=0.5,rife.target.factor=2,rife.sc=false"
```

Or even:

```conf
ctrl+i vf toggle vapoursynth=file=~~home/vapoursynth/interpolation.vpy
```


Add the following in your `~/.config/mpv/mpv.conf` or `/.var/app/io.mpv.Mpv/config/mpv.conf` for Flatpak users to have basic interpolation without MVTools
or RIFE.

```conf
interpolation=yes
```

## Modifying the script

More information:
- https://avisynth.org.ru/mvtools/mvtools2.html
- https://github.com/dubhater/vapoursynth-mvtools
- https://github.com/styler00dollar/VapourSynth-RIFE-ncnn-Vulkan.git
- https://mpv.io/manual/master/
