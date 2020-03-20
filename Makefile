all:
	docker-compose pull
	docker-compose up

build:
	docker-compose build

clean:
	docker-compose rm -vsf

distclean: clean
	docker volume rm -f kiss-cache-db kiss-cache-cache

upgrade:
	docker-compose pull
	docker-compose run --rm web python3 manage.py migrate
	docker-compose up -d --remove-orphans
