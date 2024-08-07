FROM --platform=$BUILDPLATFORM python:alpine3.20
RUN apk add --no-cache build-base linux-headers pcre-dev

WORKDIR /scrapper

COPY . /scrapper
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r requirements.txt

RUN chown nobody:nobody /scrapper -R
USER nobody
EXPOSE 9866
#Test uwsgi install
RUN uwsgi --version

CMD ["uwsgi","--ini","app.ini"]