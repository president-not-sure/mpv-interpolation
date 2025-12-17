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

Options are passed to the VapourSynth script via mpv's shortcuts, which are set using the user-data key. The user-data string consists of key-value pairs, with each pair separated by `=` and individual pairs separated by `,`.

### library

- description: Sets the interpolation library.
- valid values: mvtools, rife
- default: mvtools

### fps_factor

- description: Sets the factor by which the video frame rate will be multiplied.
- valid values: >= 1.0
- default: 2.0

### display_factor

- description: Sets the scale of the video to fit within the display resolution, downscaling it proportionally to the display size. It never upscales the video.
- valid values: 0.01 to 1.0
- default: 1.0

### Examples

Add the following in your `~/.config/mpv/input.conf` or `/.var/app/io.mpv.Mpv/config/mpv/input.conf` for Flatpak users. `~~home/` is mpv's config directory. Options can be omitted to set defaults.

```conf
ctrl+m vf toggle vapoursynth=file=~~home/vapoursynth/interpolation.vpy:user-data="library=mvtools,display_factor=1.0,fps_factor=2"
ctrl+M vf toggle vapoursynth=file=~~home/vapoursynth/interpolation.vpy:user-data="library=rife,display_factor=0.5,fps_factor=2"
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
