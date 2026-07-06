FROM postgis/postgis:15-3.3

# 로케일 설정 및 pgvector 빌드 필수 종속성 통합 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    locales \
    postgresql-server-dev-15 \
    git \
    build-essential \
    clang-11 \
    llvm-11 \
    && localedef -i ko_KR -c -f UTF-8 -A /usr/share/locale/locale.alias ko_KR.UTF-8 \
    && cd /tmp \
    && git clone --branch v0.4.4 https://github.com/pgvector/pgvector.git \
    && cd pgvector \
    && make \
    && make install \
    && apt-get remove -y postgresql-server-dev-15 git build-essential clang-11 llvm-11 \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* /tmp/pgvector

ENV LANG=ko_KR.UTF-8
ENV LC_ALL=ko_KR.UTF-8