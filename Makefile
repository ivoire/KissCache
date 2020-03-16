all:
	docker-compose build
	docker-compose up

clean:
	docker-compose rm -vsf

distclean: clean
	docker volume rm -f kiss-cache-db kiss-cache-cache
