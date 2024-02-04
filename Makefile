postgres:
	docker stop analyzer-postgres || true
	docker run --rm --detach --name=analyzer-postgres \
		--env POSTGRES_USER=admin \
		--env POSTGRES_PASSWORD=admin \
		--env POSTGRES_DB=analyzer \
		--publish 5432:5432 postgres
