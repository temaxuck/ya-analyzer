PROJECT_NAME ?= ya-analyzer
VERSION = $(shell python3 setup.py --version | tr '+' '-')
PROJECT_NAMESPACE ?= temaxuck
REGISTRY_IMAGE ?= $(PROJECT_NAMESPACE)/$(PROJECT_NAME)

network:
	docker network create analyzer-api

postgres: 
	docker stop analyzer-postgres || true
	docker run --rm --detach --name=analyzer-postgres --network=analyzer-api \
		--env POSTGRES_USER=admin \
		--env POSTGRES_PASSWORD=admin \
		--env POSTGRES_DB=analyzer \
		--publish 5432:5432 postgres

clean: 
	rm -fr *.egg-info dist

lint:
	venv/bin/pylama

sdist: clean
	python3 setup.py sdist

docker_build: sdist
	docker build --target=api -t $(PROJECT_NAME):$(VERSION) .

docker_run: docker_build
	docker run --name=analyzer-api --network=analyzer-api -d --publish 8080:8080 ya-analyzer:$(VERSION)

docker_upload: docker_build
	docker tag $(PROJECT_NAME):$(VERSION) $(REGISTRY_IMAGE):$(VERSION)
	docker tag $(PROJECT_NAME):$(VERSION) $(REGISTRY_IMAGE):latest
	docker push $(REGISTRY_IMAGE):$(VERSION)
	docker push $(REGISTRY_IMAGE):latest