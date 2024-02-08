# Base image
FROM ubuntu:jammy

# Maintain the shell setting from the official Dockerfile for error handling
SHELL ["/bin/bash", "-xo", "pipefail", "-c"]

# Set a non-interactive frontend to avoid geographical area selection prompts
ENV DEBIAN_FRONTEND=noninteractive

# Preconfigure tzdata
ENV TZ=Etc/UTC

# Install necessary tools and libraries
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    software-properties-common \
    ca-certificates \
    curl \
    dirmngr \
    fonts-noto-cjk \
    gnupg \
    libssl-dev \
    node-less \
    npm \
    xz-utils \
    git \
    postgresql-client \
    sudo && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    libpq-dev \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    libldap2-dev \
    libsasl2-dev \
    libtiff5-dev \
    libopenjp2-7-dev \
    liblcms2-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Configure locale
ENV LANG C.UTF-8

# Create the odoo user and group
RUN groupadd -g 1000 odoo && \
    useradd -u 1000 -g odoo -m -d /opt/odoo -s /bin/bash odoo && \
    echo 'odoo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Setup Python virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3.11 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Clone Odoo source code
WORKDIR /opt/odoo
RUN git clone --depth=1 --branch=17.0 https://github.com/odoo/odoo.git odoo17

# Upgrade pip and Install Odoo requirements within the virtual environment
WORKDIR /opt/odoo/odoo17
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Install wkhtmltopdf based on architecture as root
USER root
ARG TARGETARCH
RUN if [ -z "${TARGETARCH}" ]; then \
    TARGETARCH="$(dpkg --print-architecture)"; \
    fi; \
    WKHTMLTOPDF_ARCH=${TARGETARCH} && \
    case ${TARGETARCH} in \
    "amd64") WKHTMLTOPDF_ARCH=amd64 && WKHTMLTOPDF_SHA=967390a759707337b46d1c02452e2bb6b2dc6d59  ;; \
    "arm64")  WKHTMLTOPDF_SHA=90f6e69896d51ef77339d3f3a20f8582bdf496cc  ;; \
    "ppc64le" | "ppc64el") WKHTMLTOPDF_ARCH=ppc64el && WKHTMLTOPDF_SHA=5312d7d34a25b321282929df82e3574319aed25c  ;; \
    esac \
    && curl -o wkhtmltox.deb -sSL https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.jammy_${WKHTMLTOPDF_ARCH}.deb \
    && echo ${WKHTMLTOPDF_SHA} wkhtmltox.deb | sha1sum -c - \
    && apt-get update && apt-get install -y --no-install-recommends ./wkhtmltox.deb && \
    rm -rf /var/lib/apt/lists/* wkhtmltox.deb
RUN npm install -g rtlcss

# Copy and install additional Odoo dependencies via pip (requirements could be adjusted)
RUN mkdir -p /mnt/extra-addons /mnt/filestore
RUN chown -R odoo:odoo /mnt/extra-addons /mnt/filestore
COPY --chown=odoo:odoo ./requirements.txt /mnt/extra-addons/
COPY --chown=odoo:odoo ./requirements-dev.txt /mnt/extra-addons/
RUN pip install -r /mnt/extra-addons/requirements.txt && \
    pip install -r /mnt/extra-addons/requirements-dev.txt

# Copy your entrypoint script
COPY --chown=odoo:odoo ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Make port 8069 available to the world outside this container
EXPOSE 8069 8071 8072 5678

RUN mkdir -p /usr/share/GeoIP
COPY ./GeoLite2-City.mmdb /usr/share/GeoIP
COPY ./GeoLite2-Country.mmdb /usr/share/GeoIP  

USER odoo

# Ensure ENTRYPOINT points to your entrypoint script
ENTRYPOINT ["/entrypoint.sh"]
CMD ["/opt/odoo/odoo17/odoo-bin", "-c", "/etc/odoo/odoo.conf", "-u", "product_connect"]
