FROM rust:1.85-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    file \
    pkg-config \
    libssl-dev \
    libwebkit2gtk-4.1-dev \
    libgtk-3-dev \
    libayatana-appindicator3-dev \
    librsvg2-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY src-tauri/Cargo.toml src-tauri/Cargo.lock* ./
COPY src-tauri/src ./src
COPY src-tauri/build.rs ./build.rs
COPY src-tauri/tauri.conf.json ./tauri.conf.json

RUN cargo build --release

CMD ["/app/target/release/cherenkov-desktop"]
