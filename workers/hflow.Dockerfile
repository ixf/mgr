# docker build . -t hflow -f hflow.Dockerfile
FROM hyperflowwms/hyperflow
RUN apk add docker
