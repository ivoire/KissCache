all:
	docker-compose build
	docker-compose up

clean:
	docker-compose rm -vsf

distclean: clean
	docker volume rm -f kiss-cache-db kiss-cache-cache

upgrade:
	docker-compose pull
	docker-compose run web python3 manage.py migrate
	docker-compose up -d --remove-orphans
