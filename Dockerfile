FROM quay.io/fedora/fedora:latest AS build

WORKDIR /workdir

# Install dependendcies
RUN dnf -y update && \
    dnf -y install \
        git \
        meson \
        cmake \
        nasm \
        g++ \
        libstdc++-static \
        fftw-static \
        vapoursynth-devel \
        vulkan-loader-devel && \
    mkdir -p /output

# Link static libraries and enable position independent code
ENV CFLAGS="$CFLAGS -fPIC -static-libgcc -static-libstdc++"
ENV CXXFLAGS="$CXXFLAGS -fPIC -static-libgcc -static-libstdc++"
ENV LDFLAGS="$LDFLAGS /usr/lib64/libfftw3f.a /usr/lib64/libfftw3f_threads.a"

# Build mvtools
RUN git clone --depth 1 https://github.com/dubhater/vapoursynth-mvtools.git && \
    cd vapoursynth-mvtools || exit 1 && \
    meson setup build && \
    ninja -C build && \
    cp -afv build/libmvtools.so /output

# Build VapourSynth-RIFE-ncnn-Vulkan and download the models
RUN git clone https://github.com/styler00dollar/VapourSynth-RIFE-ncnn-Vulkan.git && \
    cd VapourSynth-RIFE-ncnn-Vulkan || exit 1 && \
    git submodule update --init --recursive --depth 1 && \
    meson setup build && \
    mv models build/ && \
    ninja -C build && \
    cp -afv build/librife.so build/models /output
