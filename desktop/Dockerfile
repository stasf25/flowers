FROM accupara/qt6:ubuntu_2204_x86_64
#FROM stateoftheartio/qt6:6.6-gcc-aqt
ENV QMAKE=/opt/Qt/6.6.1/gcc_64/bin/qmake
WORKDIR /work
USER root

# Python 3.10 + pip + file
# + шрифты с кириллицей (DejaVu Sans покроет 'Segoe UI', Arial, sans-serif из styles.py)
#RUN apt-get update && apt-get install -y software-properties-common \
# && add-apt-repository -y ppa:deadsnake/ppa \
# && apt-get update && apt-get install -y python3.10 python3.10-venv python3.10-dev python3-pip file fonts-dejavu-core \
# && rm -rf /var/lib/apt/lists/*
RUN apt update && apt install -y libxcb-cursor0 python3.10-venv python3.10-dev python3-pip file fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

USER 1000:1000
