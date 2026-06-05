.PHONY: demo full

demo:
	docker compose --profile demo up

full:
	docker compose --profile full up
