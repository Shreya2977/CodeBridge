FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Fortran compiler + Python 3 in one image so both source (A) and target (B)
# can be compiled/run without spinning up two separate containers.
RUN apt-get update && apt-get install -y \
    gfortran \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Non-root user so a runaway candidate program can't do much damage
RUN useradd -m sandboxuser
USER sandboxuser
WORKDIR /home/sandboxuser

# Keep the container alive so we can `docker exec` into it repeatedly
# instead of paying container-startup cost on every single test run.
CMD ["sleep", "infinity"]
