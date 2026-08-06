FROM postgis/postgis:15-3.3

# 로케일 설정 및 official postgresql-15-pgvector 패키지 통합 설치 (Make 빌드 파기 exit code 2 완전 예방)
RUN apt-get update && apt-get install -y --no-install-recommends \
    locales \
    postgresql-15-pgvector \
    && localedef -i ko_KR -c -f UTF-8 -A /usr/share/locale/locale.alias ko_KR.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=ko_KR.UTF-8
ENV LC_ALL=ko_KR.UTF-8