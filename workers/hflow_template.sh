# set HF_VAR_WORKER_CONTAINER=
# set HF_VAR_WORK_DIR
# set --name

docker run -a stdout -a stderr --rm --network container:redis \
	-e HF_VAR_WORKER_CONTAINER="hyperflowwms/soykb-worker" \
	-e HF_VAR_WORK_DIR="$PWD/sources/soykb-input" \
	-e HF_VAR_HFLOW_IN_CONTAINER="true" \
	-e HF_VAR_function="redisCommand" \
	-e REDIS_URL="redis://127.0.0.1:6379" \
	--name hyperflow \
	-v /var/run/docker.sock:/var/run/docker.sock \
	-v $PWD/workers/soykb:/wfdir \
	--entrypoint "/bin/sh" hflow -c "hflow run /wfdir"
