# mgr

Requirements to run any of this are defined by the Vagrantfile.

## Directories/files
- od/ - environment simulator
  - od/fs/ - FUSE and Cache
  - od/methods/ - prediction methods
  - od/specs/ - unit tests
  - od/stats/ - helpers functions for doing analysis in notebooks
- sources/ - directory for sample files
- target/ - empty directory as a target for mounting
- workers/ - programs for recording reads
- envs.yml - configuration of simulated environments

```
docker pull hyperflowwms/hyperflow:v1.5.7
docker pull hyperflowwms/soykb-worker
docker pull redis:latest
docker run -d --name redis redis --bind 127.0.0.1
cd misc && docker build . -t hf
```

```
docker kill (docker ps -a -q)
docker rm (docker ps -a -q)
docker run -d --name redis redis --bind 127.0.0.1
```
