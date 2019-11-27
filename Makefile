all:
	docker-compose build
	docker-compose up --scale web=2

clean:
	docker-compose rm -vsf
	docker volume rm -f kiss-cache-db kiss-cache-cache
