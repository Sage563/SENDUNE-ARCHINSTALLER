FROM archlinux:latest

RUN pacman -Syu --noconfirm && \
    pacman -S --noconfirm archiso git base-devel && \
    pacman -Scc --noconfirm

WORKDIR /build

CMD ["/bin/bash"]
